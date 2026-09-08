"""Fresh repaired-MFV L4 short validation, direct Windows raw storage.

Six NEW short diagnostics only. No full-pair launch, old-data mutation or rebuild.
"""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import time

import h5py
import numpy as np
import psutil
import mfv_l4_native_checks as v
from mfv_l4_native_checks import check,sha,save,safe,parameters
from storage_guard import windows_backing_volume

HERE=Path(__file__).resolve().parent
BASE=Path('/home/kaan/sensitivity_20260907/gizmo')
PACKAGE=BASE/'mfv_timestep_repair_v1/l4_prepare_runner_v1'
RAW=Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/mfv_L4_preparation_v1')
GIB=1024**3
RESERVE=10*GIB
ANCILLARY=GIB
PREP_PLAN_SHA='74c54e9db5785752e3193e3130e5d2a3ae94474262ce6121b24e6564adbbe6e8'
L3_REPORT_SHA='db45f9d985a4e8eb87b63f0247d1d5f61572acfaab5dad6f9272dfe36b0a017d'
IC_SOURCES=[BASE/'full_mfm_l4_v1'/law/'ics.hdf5' for law in ('sharp13','tanh13')]
ARCHIVE=Path('/home/kaan/codes/gizmo/runs/GZ_L4_chi100_mfv/ics.hdf5')
CASES=[dict(name=f'{law}_{role}',mode=mode,role=role) for mode,law in enumerate(('sharp13','tanh13'))
       for role in ('smoke','timing_full','timing_half')]


def progress(report):
    """Only this new batch ledger is mutable; completed validation is immutable."""
    temp=RAW/'batch.json.tmp';new_target(temp);save(temp,report);temp.replace(RAW/'batch.json')


def new_target(path):
    check(not Path(path).exists(),'Existing destination must not be overwritten or resumed')


def mapping(mount,host,raw_device,guest_device):
    check(mount['target']=='/mnt/c' and mount['source']=='C:\\' and mount['fstype']=='9p'
          and 'aname=drvfs;path=C:\\;' in mount['options'] and 'rw' in mount['options'].split(','),'Unexpected Windows raw mount')
    check(host['drive']=='C:' and raw_device!=guest_device,'Wrong host/raw device')


def budget_gate(guest,mounted,host,remaining,live=False):
    check(all(type(x) is int and x>=0 for x in (guest,mounted,host,remaining)),'Invalid capacity/budget measurement')
    check(guest>=RESERVE+(0 if live else ANCILLARY),'Guest reserve/ancillary capacity fails')
    check(min(mounted,host)>=RESERVE+(0 if live else ANCILLARY+remaining),'Host payload/reserve/ancillary capacity fails')


def storage(remaining,live=False):
    parent=Path('/mnt/c/Users/kaanb/CloudCrushing')
    check(parent.resolve()==parent and BASE.resolve()==BASE,'Unexpected root symlink')
    mount=json.loads(subprocess.check_output(['findmnt','-J','-T',str(parent),'-o','TARGET,SOURCE,FSTYPE,OPTIONS'],text=True))['filesystems']
    check(len(mount)==1,'Ambiguous raw mount');host=windows_backing_volume()
    mapping(mount[0],host,parent.stat().st_dev,BASE.stat().st_dev)
    guest=shutil.disk_usage(BASE).free;mounted=shutil.disk_usage(parent).free
    budget_gate(guest,mounted,host['free_bytes'],remaining,live)
    return dict(guest_free_bytes=guest,mounted_free_bytes=mounted,windows=host,mount=mount[0],remaining_bytes=remaining,live=live)


def no_competing():
    found=[]
    for proc in psutil.process_iter(['name','pid','status']):
        name=(proc.info['name'] or '').lower()
        if proc.info['status']!=psutil.STATUS_ZOMBIE and (name.startswith(('gizmo','gadget','athena','enzo','flash','ramses','arepo','gasoline')) or name in ('make','cc1','cc1plus','f951')):
            found.append(proc.info)
    check(not found,'Competing native solver/build '+str(found))


def locks():
    held=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(handle)
    return held


def input_values(text,p,role):
    check(role in ('smoke','timing_full','timing_half','full'),'Wrong role')
    values=parameters(text)
    expected={'MaxMemSize':1500,'PartAllocFactor':2.5,'MaxSizeTimestep':.05,'MinSizeTimestep':1e-12,
        'CpuTimeBetRestartFile':3600,'TimeLimitCPU':604800,'MinGasTemp':0,'InitGasTemp':0,
        'TimeBegin':0,'TimeOfFirstSnapshot':0,'OutputListOn':0,'NumFilesPerSnapshot':1,
        'NumFilesWrittenInParallel':1,'ICFormat':3,'SnapFormat':3,'BoxSize':10,'DesNumNgb':32}
    expected.update({f'Softening_Type{i}':v.DX for i in range(6)})
    check(all(float(values[k])==x for k,x in expected.items()),'Changed original L4 numerical setting')
    check(all(values[k]==x for k,x in dict(InitCondFile='ics',OutputDir='output',RestartFile='restart',SnapshotFileBase='snapshot').items()),'Wrong output path')
    end=5*p['t_cc'] if role=='full' else (.1 if role=='smoke' else .00004)
    values.update(TimeMax=repr(end),TimeBetSnapshot=repr(.05*p['t_cc'] if role=='full' else end))
    if role.startswith('timing'):values['MaxSizeTimestep']='1e-5' if role=='timing_full' else '5e-6'
    return values


def dependencies():
    check(sha(v.BINARY)==v.BINARY_SHA,'Native repaired executable changed')
    check(sha(v.PREP/'plan.json')==PREP_PLAN_SHA,'Completed helper plan changed')
    prior=json.loads((v.PREP/'plan.json').read_text())
    for name,digest in prior['files'].items():check(sha(v.PREP/name)==digest,'Frozen helper changed '+name)
    for name,digest in v.prior.onset.PINNED_SOURCE.items():check(sha(v.BINARY.parent/name)==digest,'Native source changed '+name)
    report=BASE/'mfv_timestep_repair_v1/sharp_full_native_v1/pair_validation.json'
    check(sha(report)==L3_REPORT_SHA,'Accepted repaired L3 evidence changed')
    build=json.loads((BASE/'build.json').read_text())
    for name in ('experiment.json','params_mfv_L4.txt'):
        check(sha(BASE/name)==build['pinned_files'][name],'Native metadata/template changed')
    p=json.loads((BASE/'experiment.json').read_text())
    check((p['chi'],p['mach'],p['gamma'],p['r_cloud'],p['mass_mode'],p['ranks'])==(100,2,5/3,1,'volume',8),'Unexpected physics')
    p['v_wind']=p['mach']*math.sqrt(p['gamma']*p['p_wind']/p['rho_wind']);p['t_cc']=math.sqrt(p['chi'])*p['r_cloud']/p['v_wind']
    full=json.loads(report.read_text());check(full['physics']==p,'L3/L4 physical metadata differs')
    return p,prior


def freeze():
    new_target(PACKAGE);new_target(RAW);held=locks();no_competing()
    p,prior=dependencies()
    # Upper screen from the measured L3 short budget, scaling even fixed costs8x.
    # Six short cases only; NO full-pair capacity promise before L4 measurement.
    per_case=8*int(prior['short_case_bytes']);before=storage(6*per_case)
    check(psutil.virtual_memory().available>=16*GIB,'Preflight RAM below native allocation plus reserve')
    check(RAW.parent.exists() and RAW.parent.resolve()==RAW.parent,'Unreviewed raw parent')
    a,_=v.read(IC_SOURCES[0],False);b,_=v.read(IC_SOURCES[1],False);old,_=v.read(ARCHIVE,False)
    laws=[v.ic_law(a,p,0),v.ic_law(b,p,1)];v.prior.same_fields(a,b,('Velocities',));v.prior.same_fields(b,old)
    with h5py.File(IC_SOURCES[0]) as x,h5py.File(IC_SOURCES[1]) as y,h5py.File(ARCHIVE) as z:
        check(set(x['Header'].attrs)==set(y['Header'].attrs)==set(z['Header'].attrs),'IC header schemas differ')
        check(all(np.array_equal(x['Header'].attrs[k],y['Header'].attrs[k]) and np.array_equal(y['Header'].attrs[k],z['Header'].attrs[k]) for k in x['Header'].attrs),'IC header values differ')
    PACKAGE.mkdir();RAW.mkdir();(RAW/'inputs').mkdir();(RAW/'scratch').mkdir()
    names=['mfv_l4_prepare.py','mfv_l4_native_checks.py','test_mfv_l4_prepare.py','MFV_L4_PREPARATION_PLAN.md']
    for name in names:shutil.copy2(HERE/name,PACKAGE/name)
    readback={}
    for mode,law in enumerate(('sharp13','tanh13')):
        target=RAW/'inputs'/f'{law}.hdf5';shutil.copy2(IC_SOURCES[mode],target)
        check(sha(target)==sha(IC_SOURCES[mode]),'IC copy mismatch');readback[str(target.relative_to(RAW))]=sha(target)
    for role in ('smoke','timing_full','timing_half','full'):
        target=RAW/'inputs'/f'{role}.txt'
        with target.open('x') as out:out.write(''.join(f'{k:32s} {val}\n' for k,val in input_values((BASE/'params_mfv_L4.txt').read_text(),p,role).items()))
        readback[str(target.relative_to(RAW))]=sha(target)
    pins={str(PACKAGE/n):sha(PACKAGE/n) for n in names}
    for path in (v.BINARY,v.PREP/'plan.json',BASE/'build.json',BASE/'experiment.json',BASE/'params_mfv_L4.txt',ARCHIVE,*IC_SOURCES):pins[str(path)]=sha(path)
    for name in prior['files']:pins[str(v.PREP/name)]=sha(v.PREP/name)
    for name in v.prior.onset.PINNED_SOURCE:pins[str(v.BINARY.parent/name)]=sha(v.BINARY.parent/name)
    for name,digest in readback.items():pins[str(RAW/name)]=digest
    tests=subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_l4_prepare'],cwd=PACKAGE,capture_output=True,text=True,timeout=60)
    save(PACKAGE/'tests.json',dict(returncode=tests.returncode,stdout=tests.stdout,stderr=tests.stderr))
    check(tests.returncode==0 and 'Ran 23 tests' in tests.stderr and '\nOK\n' in tests.stderr,'New L4 tests failed')
    pins[str(PACKAGE/'tests.json')]=sha(PACKAGE/'tests.json')
    plan=dict(status='frozen_short_only_needs_windows_readback',physics=p,levels=[4],native_count=v.N,binary_sha256=v.BINARY_SHA,
        pins=pins,windows_readback_files=readback,cases=CASES,case_bytes=per_case,all_short_bytes=6*per_case,guest_ancillary_bytes=ANCILLARY,
        initial_checks=laws,historical_archived_arrays_exact=True,nonvelocity_ic_fields_exact=True,storage_before=before,
        storage_after=storage(6*per_case),tests=23,native_runs_started=0,full_pair_reserved=False,
        scope='Six fresh repaired L4 diagnostics only. No full controls enabled; no old native run repeated; all raw retained.')
    save(PACKAGE/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],plan_sha256=sha(PACKAGE/'plan.json'),short_budget_gib=6*per_case/GIB,tests=23)),flush=True)


def frozen(plan):
    check(HERE==PACKAGE and plan['status']=='frozen_short_only_needs_windows_readback','Wrong frozen scope')
    for path,digest in plan['pins'].items():check(sha(path)==digest,'Changed frozen pin '+path)
    check(RAW.resolve()==RAW and RAW.parent.resolve()==RAW.parent,'Wrong raw path')
    dependencies()


def ownership(pid,created,current_created,pgid):
    check(current_created==created and pgid==pid,'Process identity/group changed')


def stop_owned(proc,created,folder):
    if proc.poll() is not None:return
    ownership(proc.pid,created,psutil.Process(proc.pid).create_time(),os.getpgid(proc.pid))
    (folder/'output').mkdir(exist_ok=True);(folder/'output/stop').touch(exist_ok=False)
    try:proc.wait(timeout=30);return
    except subprocess.TimeoutExpired:pass
    for sig in (signal.SIGTERM,signal.SIGKILL):
        if proc.poll() is not None:return
        ownership(proc.pid,created,psutil.Process(proc.pid).create_time(),os.getpgid(proc.pid));os.killpg(proc.pid,sig)
        try:proc.wait(timeout=15);return
        except subprocess.TimeoutExpired:pass
    raise RuntimeError('Owned solver did not exit')


def execute(case,plan):
    frozen(plan);no_competing();storage(plan['case_bytes']);check(psutil.virtual_memory().available>=16*GIB,'RAM preflight')
    folder=RAW/case['name'];new_target(folder);folder.mkdir();law='tanh13' if case['mode'] else 'sharp13'
    shutil.copy2(RAW/'inputs'/f'{law}.hdf5',folder/'ics.hdf5');shutil.copy2(RAW/'inputs'/f"{case['role']}.txt",folder/'params.txt')
    record=dict(case=case,directory=str(folder),binary_sha256=v.BINARY_SHA,ic_sha256=sha(folder/'ics.hdf5'),
        input_sha256=sha(folder/'params.txt'),plan_sha256=sha(PACKAGE/'plan.json'),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    command=['mpirun','--bind-to','core','-np','8',str(v.BINARY),'params.txt'];record['command']=command;save(folder/'launch.json',record)
    peak=0;prev={};lastsample=None;busy=[];lastdisk=0;proc=None;failure=None;start=time.monotonic()
    print('START '+case['name'],flush=True)
    try:
        with (folder/'run.log').open('x') as out,(folder/'resources.jsonl').open('x') as res:
            proc=subprocess.Popen(command,cwd=folder,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TMPDIR=str(RAW/'scratch')))
            handle=psutil.Process(proc.pid);created=handle.create_time();save(folder/'process.json',dict(pid=proc.pid,create_time=created))
            while proc.poll() is None:
                now=time.monotonic();rss=0;current={}
                try:children=handle.children(recursive=True)
                except psutil.NoSuchProcess:proc.wait(timeout=5);break
                for child in children:
                    try:
                        ct=child.cpu_times();current[(child.pid,child.create_time())]=ct.user+ct.system;rss+=child.memory_info().rss
                    except psutil.NoSuchProcess:pass
                cores=None if not prev else sum(max(0,c-prev[k]) for k,c in current.items() if k in prev)/(now-lastsample)
                if cores is not None:busy.append(cores)
                prev,lastsample=current,now;peak=max(peak,rss)
                res.write(json.dumps(dict(elapsed_seconds=now-start,child_rss_bytes=rss,busy_cpu_workers=cores))+'\n');res.flush()
                check(now-start<180,'Native diagnostic wall cap');check(psutil.virtual_memory().available>=2*GIB,'Live RAM reserve')
                if now-lastdisk>=10:storage(0,True);lastdisk=time.monotonic()
                try:proc.wait(timeout=.25)
                except subprocess.TimeoutExpired:pass
    except BaseException as exc:
        failure=repr(exc)
        if proc is not None and proc.poll() is None:stop_owned(proc,created,folder)
    record.update(status='native_finished_pending_checks' if proc is not None and proc.returncode==0 and failure is None else 'failed',
        returncode=proc.returncode if proc else None,error=failure,wall_seconds=time.monotonic()-start,
        peak_child_rss_bytes=peak,median_busy_cpu_workers=statistics.median(busy) if busy else None)
    save(folder/'result.json',record);check(record['status']=='native_finished_pending_checks','Native failed; retained '+str(failure))
    log=(folder/'run.log').read_text();flags=json.loads((BASE/'build.json').read_text())['expected_config']['mfv']
    check(all(s in log for s in flags) and 'HYDRO_MESHLESS_FINITE_MASS' not in log and 'Simulation ends.' in log and 'Final time=' in log,'Native provenance/exit markers')
    ic,_=v.read(folder/'ics.hdf5',False);initial,report=v.audit(folder,plan['physics'],ic)
    frozen(plan);check(sha(folder/'params.txt')==record['input_sha256'] and sha(folder/'ics.hdf5')==record['ic_sha256'],'Inputs changed')
    report.update(case=case,resources=record,status='passed_short_native_checks',input_sha256=record['input_sha256'],ic_sha256=record['ic_sha256'])
    save(folder/'validation.json',report)
    print(f"FINISH {case['name']}: {len(report['rows'])} actual states, {record['wall_seconds']:.2f}s native, peak {peak/GIB:.3f}GiB",flush=True)
    return report,initial


def run():
    new_target(RAW/'batch.json');held=locks();no_competing()
    plan=json.loads((PACKAGE/'plan.json').read_text());frozen(plan)
    win=json.loads((RAW/'windows_readback.json').read_text(encoding='utf-8-sig'))
    check(win['plan_sha256']==sha(PACKAGE/'plan.json') and win['hashes']==plan['windows_readback_files'],'Missing/mismatched independent Windows readback')
    storage(plan['all_short_bytes']);report=dict(status='running',plan_sha256=sha(PACKAGE/'plan.json'),cases=[],full_controls_added=0)
    save(RAW/'batch.json',report);initials={}
    import tempfile
    tempfile.tempdir=str(RAW/'scratch')
    try:
        for index,case in enumerate(plan['cases']):
            storage((6-index)*plan['case_bytes'])
            report['active_case']=case['name'];progress(report)
            result,initial=execute(case,plan);report['cases'].append(result);initials[case['name']]=initial
            report.pop('active_case',None);progress(report)
        for role in ('smoke','timing_full','timing_half'):
            v.prior.same_fields(initials['sharp13_'+role],initials['tanh13_'+role],('Velocities','ParticleVelocities'))
            a,b=[next(c for c in report['cases'] if c['case']['name']==law+'_'+role) for law in ('sharp13','tanh13')]
            check(a['input_sha256']==b['input_sha256'],'Paired diagnostic parameters differ')
        timing={}
        for mode,law in enumerate(('sharp13','tanh13')):
            ic,_=v.read(RAW/'inputs'/f'{law}.hdf5',False)
            for role in ('timing_full','timing_half'):
                v.prior.same_fields(initials[law+'_smoke'],initials[law+'_'+role],('Velocities','ParticleVelocities'))
            timing[law]=v.prior.scaling(ic['Velocities'],initials[law+'_timing_full']['Velocities'],initials[law+'_timing_half']['Velocities'])
        snap=max(r['bytes'] for c in report['cases'] for r in c['rows'])
        restart=max(sum(f['bytes'] for f in c['terminal']['files']) for c in report['cases'])
        ic=max((RAW/'inputs'/f'{law}.hdf5').stat().st_size for law in ('sharp13','tanh13'))
        full=2*math.ceil(1.25*(104*snap+3*restart+ic+256*1024**2))
        try:gate=dict(passed=True,storage=storage(full))
        except Exception as exc:gate=dict(passed=False,error=str(exc))
        report.update(status='passed_L4_short_preparation_not_full_pair',timing=timing,native_states=sum(len(c['rows']) for c in report['cases']),
            full_pair_budget=dict(bytes=full,snapshot_bytes=snap,restart_set_bytes=restart,ic_bytes=ic,
                formula='2 laws * (104snapshots +3eight-rank restart sets +IC +256MiB logs) *1.25; separate1GiB ancillary and10GiB host/guest reserves'),
            full_pair_storage_gate=gate,scope='Six short L4 diagnostics only. Retained raw, no native rerun or full-pair admission. Staggered velocities, periodic boundaries; no physical-accuracy/convergence claim.')
        frozen(plan);save(RAW/'validation.json',report);progress(report)
        print(json.dumps(dict(status=report['status'],native_states=report['native_states'],timing=timing,full_pair_gib=full/GIB,full_pair_gate=gate)),flush=True)
    except BaseException as exc:
        report.update(status='needs_review',error=repr(exc));save(RAW/'failure.json',report);progress(report);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);args=parser.parse_args()
    (freeze if args.mode=='freeze' else run)()
