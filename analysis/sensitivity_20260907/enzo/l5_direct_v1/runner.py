"""New native Enzo L5 pair; no old queue replay or source/raw modifications."""
import argparse
import fcntl
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import time

import psutil

HERE = Path(__file__).resolve().parent
STUDY = Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
GUEST = Path('/home/kaan/sensitivity_20260907/enzo')
RAW = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/enzo_L5_velocity_pair_v1')
HOST_ROOT = Path('/mnt/c/Users/kaanb/CloudCrushing')
BINARY = GUEST/'enzo_pair'
BINARY_SHA = '28d482af94828aba1de2b097068b66c9ec80b88b53bd6405e0ff96fbecf57900'
GIB = 1024**3
RESERVE = 10*GIB
ANCILLARY = GIB
DIAGNOSTICS = 2*GIB


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)


def helpers():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import run_enzo as e
    import analyze_enzo as a
    return e, a


def verify_path(path=RAW):
    require(path == RAW and path.resolve() == path, 'Unreviewed output path')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Output symlink')


def mapping_gate(mount, host, output_device, guest_device):
    require(mount['target']=='/mnt/c' and mount['source']=='C:\\'
            and mount['fstype']=='9p' and 'aname=drvfs;path=C:\\;' in mount['options']
            and 'rw' in mount['options'].split(','), 'Unreviewed output mount')
    require(host['drive']=='C:' and output_device != guest_device, 'Wrong backing/filesystem device')


def budget_gate(guest, mounted, windows, remaining, live=False):
    require(all(type(x) is int and x >= 0 for x in (guest,mounted,windows,remaining)), 'Invalid capacity')
    require(guest >= RESERVE + (0 if live else ANCILLARY), 'Guest reserve/ancillary shortage')
    require(min(mounted,windows) >= RESERVE + (0 if live else ANCILLARY+remaining),
            'Host full-pair/reserve shortage')


def storage(remaining=0, live=False):
    sys.path.insert(0, '/home/kaan/verified_20260907')
    from storage_guard import windows_backing_volume
    verify_path()
    require(HOST_ROOT.resolve()==HOST_ROOT and GUEST.resolve()==GUEST, 'Root mapping changed')
    mounts=json.loads(subprocess.check_output(['findmnt','-J','-T',str(HOST_ROOT),
        '-o','TARGET,SOURCE,FSTYPE,OPTIONS'],text=True))['filesystems']
    require(len(mounts)==1, 'Ambiguous mount')
    host=windows_backing_volume()
    mapping_gate(mounts[0],host,HOST_ROOT.stat().st_dev,GUEST.stat().st_dev)
    guest=shutil.disk_usage(GUEST).free
    mounted=shutil.disk_usage(HOST_ROOT).free
    budget_gate(guest,mounted,host['free_bytes'],int(remaining),live)
    return dict(guest_free_bytes=guest,mounted_free_bytes=mounted,windows=host,
                remaining_budget_bytes=remaining,live=live,mount=mounts[0])


def acquire_locks():
    result=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result.append(handle)
    competing=[]
    prefixes=('athena','flash4','flashx','enzo','ramses','gizmo','gadget4','gasoline','arepo','make','cc1','gfortran','cello')
    for proc in psutil.process_iter(['pid','name']):
        if (proc.info['name'] or '').lower().startswith(prefixes):
            competing.append(proc.info)
    require(not competing,'Competing native solver/build: '+str(competing))
    return result


def check_pins(plan):
    for path,digest in plan['pins'].items():
        require(sha(path)==digest,'Pinned dependency changed: '+path)
    require(sha(BINARY)==BINARY_SHA,'Native binary changed')


def check_windows(plan):
    proof=json.loads((RAW/'windows_readback.json').read_text(encoding='utf-8-sig'))
    require(proof['plan_sha256']==sha(HERE/'plan.json'),'Wrong Windows plan readback')
    require(set(proof['hashes'])==set(plan['windows_files']),'Incomplete Windows readback')
    for name,digest in proof['hashes'].items():
        require(digest==plan['windows_files'][name]==sha(RAW/name),'Cross-platform hash mismatch')


def safe_stop(proc,identity):
    if proc.poll() is not None:
        return
    # No undocumented Enzo checkpoint signal is invented. Allow a bounded grace,
    # then terminate only the still-owned process group. Never resume partial dumps.
    try:
        proc.wait(timeout=15)
        return
    except subprocess.TimeoutExpired:
        pass
    for sig in (signal.SIGTERM,signal.SIGKILL):
        if proc.poll() is not None:
            return
        require(psutil.Process(proc.pid).create_time()==identity and os.getpgid(proc.pid)==proc.pid,
                'Process ownership changed')
        os.killpg(proc.pid,sig)
        try:
            proc.wait(timeout=15)
            return
        except subprocess.TimeoutExpired:
            pass
    raise RuntimeError('Owned native group did not stop')


def independent_check(record,a):
    checks=[]
    for row in record['series']:
        direct=a.direct(row['snapshot'],record['parameters'],[256,128,128])
        error=max(abs(direct[k]-row[k])/max(abs(row[k]),1.) for k in ('dense_mass','tracer_mass'))
        require(error<=1e-12 and abs(direct['time_code']-row['time_code'])<=1e-12,
                'Independent HDF5/yt mass or time discrepancy')
        checks.append(dict(snapshot=row['snapshot'],max_scaled_mass_error=error))
    return checks


def run_case(mode,smoke,plan):
    e,a=helpers()
    law='tanh13' if mode else 'sharp13'
    folder=RAW/('diagnostics' if smoke else 'full')/law
    require(not (folder/'result.json').exists() and not list(folder.glob('DD*')),
            'Existing run is immutable; no automatic retry')
    check_pins(plan)
    require((folder/'CloudWind.enzo').read_text()==e.input_for(5,mode,smoke),'Input changed')
    require(psutil.virtual_memory().available>=8*GIB,'RAM preflight shortage')
    preflight=storage((2-mode)*plan['case_budget_bytes']+(DIAGNOSTICS if smoke else 0))
    params=e.parse_file(folder/'CloudWind.enzo')
    command=['mpirun','--bind-to','core','-np','8',str(BINARY),'CloudWind.enzo']
    record=dict(status='running',code='Enzo',level=5,mode=mode,diagnostic=smoke,
                directory=str(folder),parameters=params,command=command,binary_sha256=BINARY_SHA,
                parameter_sha256=sha(folder/'CloudWind.enzo'),storage=preflight,
                gpu_solver=False,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    save(folder/'result.json',record)
    print('START '+str(folder),flush=True)
    start=time.monotonic();sample_at=start;guard_at=start;previous={};busy=[];peak=0;proc=None;reason=None
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
        try:
            proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TMPDIR=str(RAW/'scratch')))
            owner=psutil.Process(proc.pid);identity=owner.create_time()
            record.update(mpirun_pid=proc.pid,mpirun_create_time=identity)
            save(folder/'result.json',record)
            while proc.poll() is None:
                now=time.monotonic();rss=0;delta=0.;current={}
                try:
                    children=owner.children(recursive=True)
                except psutil.NoSuchProcess:
                    if proc.poll() is not None:
                        break
                    raise
                for child in children:
                    try:
                        rss+=child.memory_info().rss;cpu=child.cpu_times();key=(child.pid,child.create_time())
                        current[key]=cpu.user+cpu.system
                        if key in previous:delta+=max(0.,current[key]-previous[key])
                    except psutil.NoSuchProcess:
                        pass
                cores=delta/max(now-sample_at,1e-6)
                if previous:busy.append(cores)
                peak=max(peak,rss);available=psutil.virtual_memory().available
                resources.write(json.dumps(dict(elapsed_seconds=now-start,rss_bytes=rss,
                    busy_cpu_workers=cores,available_ram_bytes=available))+'\n');resources.flush()
                previous=current;sample_at=now
                require(available>=2*GIB and now-start<=(600 if smoke else 21600),'RAM/runtime guard')
                if now-guard_at>=30:
                    storage(live=True);guard_at=time.monotonic()
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:pass
        except BaseException as exc:
            reason=repr(exc)
            if proc is not None and proc.poll() is None:safe_stop(proc,identity)
        finally:
            record.update(status='stopped_needs_review' if reason else 'native_finished_pending_checks',
                returncode=proc.returncode if proc else None,error=reason,wall_seconds=time.monotonic()-start,
                peak_child_rss_gib=peak/GIB,median_busy_cpu_workers=statistics.median(busy) if busy else None)
            save(folder/'result.json',record)
    require(reason is None and proc.returncode==0,'Native process failed; all files retained')
    require(f'CloudWindVelocityIC = {mode}' in (folder/'amr.out').read_text(),'Missing runtime mode echo')
    try:
        record.update(e.validate(folder,params,5,mode,smoke))
        if smoke:
            require(record['unique_snapshots']>=2 and record['series'][-1]['time_code']>0,'No evolved diagnostic')
        record['independent_HDF5_checks']=independent_check(record,a)
        check_pins(plan)
        # Stream file hashes rather than reading payloads into memory.
        files=[]
        for file in sorted(folder.rglob('*')):
            if file.is_file() and file.name not in ('result.json','result.json.tmp'):
                files.append(dict(path=str(file),bytes=file.stat().st_size,sha256=sha(file)))
        record.update(status='complete_independent_checks',retained_files=files)
        save(folder/'result.json',record)
    except BaseException as exc:
        record.update(status='validation_needs_review',error=repr(exc));save(folder/'result.json',record)
        raise
    print(f"FINISH L5 {law} diagnostic={smoke}: {record['unique_snapshots']} states, {record['wall_seconds']:.1f}s",flush=True)
    return record


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['diagnostics','full']);args=ap.parse_args()
    locks=acquire_locks()
    plan=json.loads((HERE/'plan.json').read_text());check_pins(plan);check_windows(plan)
    smoke=args.stage=='diagnostics';ledger=RAW/(args.stage+'_batch.json')
    require(not ledger.exists(),'Existing stage ledger: no rerun')
    if not smoke:
        proof=json.loads((RAW/'diagnostics_batch.json').read_text())
        require(proof['status']=='complete_independent_pair_checks' and proof['plan_sha256']==sha(HERE/'plan.json'),
                'L5 diagnostic pair is not accepted')
        for case in proof['finished']:
            require(case['status']=='complete_independent_checks','Diagnostic case not accepted')
    storage(2*plan['case_budget_bytes']+(DIAGNOSTICS if smoke else 0))
    batch=dict(status='running',stage=args.stage,plan_sha256=sha(HERE/'plan.json'),finished=[],new_full_controls=0)
    save(ledger,batch)
    try:
        for mode in (0,1):
            batch['active_mode']=mode;save(ledger,batch)
            batch['finished'].append(run_case(mode,smoke,plan));save(ledger,batch);gc.collect()
        e,_=helpers();batch['initial_pair_checks']=e.pair_initial(*batch['finished'])
        batch.update(status='complete_independent_pair_checks',new_full_controls=0 if smoke else 2)
        batch.pop('active_mode',None)
    except BaseException as exc:
        batch.update(status='stopped_needs_review',error=repr(exc));raise
    finally:save(ledger,batch)
    print('STAGE COMPLETE '+args.stage+'; no automatic publication or other-code queue.',flush=True)


if __name__=='__main__':main()
