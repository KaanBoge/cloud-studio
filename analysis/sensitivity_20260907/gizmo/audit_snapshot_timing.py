"""Small, isolated timestep-scaling test of GIZMO's native t=0 velocity output.

No native source, production input, existing raw state or executable is changed.
Only diagnostic TimeMax/output interval/MaxSizeTimestep differ from the smokes.
"""
import fcntl,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import psutil
from smoke_gizmo import ROOT,sha,save,physics,params,read,generate,require_storage,storage_snapshot,GIB
from verify_gizmo import native,snapshots

def scaling_check(ic,vfull,vhalf):
    ic,vfull,vhalf=(np.asarray(v,dtype=float) for v in (ic,vfull,vhalf))
    if ic.shape!=vfull.shape or ic.shape!=vhalf.shape or not all(np.all(np.isfinite(v)) for v in (ic,vfull,vhalf)):
        raise ValueError('Invalid velocity arrays')
    d1=vfull-ic;d2=vhalf-ic
    norm=float(np.linalg.norm(d1))
    if np.max(abs(d1))<1e-6 or norm==0:raise ValueError('Test is not discriminating')
    ratio=float(np.linalg.norm(d2)/norm)
    bound=float(4*np.finfo(np.float32).eps*max(1.,float(np.max(abs(ic)))))
    residual=float(np.max(abs(2*vhalf-vfull-ic)))
    if abs(ratio-.5)>.002 or residual>bound:raise ValueError('Velocity change does not scale as a half-step kick')
    return dict(norm_ratio=ratio,zero_step_extrapolation_max_error=residual,float32_roundoff_bound=bound,
                full_step_max_delta=float(np.max(abs(d1))),half_step_max_delta=float(np.max(abs(d2))))

def run_diagnostic(variant,mode,cap,base,allow_existing=False):
    p=physics();build=json.loads((ROOT/'build.json').read_text())
    name=f'{variant}_{mode}_{cap:g}';folder=base/name
    if folder.exists():
        if not allow_existing:raise ValueError('Existing diagnostic must be retained, not overwritten')
        record=json.loads((folder/'result.json').read_text())
        if record['status']!='collected_pending_scaling_check' or (record['variant'],record['mode'],record['max_timestep'])!=(variant,mode,cap):
            raise ValueError('Cannot reuse an incomplete or different diagnostic')
        if record['returncode']!=0 or sha(folder/'params.txt')!=record['input_sha256'] or sha(folder/'ics.hdf5')!=record['ic_sha256']:
            raise ValueError('Completed diagnostic provenance changed')
        binary=ROOT/f'GIZMO_{variant}_pair'
        if sha(binary)!=record['binary_sha256'] or sha(binary)!=build['pinned_files'][binary.name]:raise ValueError('Binary changed')
        paths=snapshots(folder/'output')
        if [str(x) for x in paths]!=record['snapshots'] or [native(x,p,variant)[1] for x in paths]!=record['native_times']:
            raise ValueError('Completed diagnostic outputs changed')
        return record
    require_storage(storage_snapshot(ROOT),GIB)
    old=ROOT/'smokes'/f'L3_{variant}_{"tanh13" if mode else "sharp13"}'
    old_record=json.loads((old/'result.json').read_text())
    if sha(old/'params.txt')!=old_record['input_sha256'] or sha(old/'ics.hdf5')!=old_record['ic_sha256']:
        raise ValueError('Original smoke inputs changed')
    values=params((old/'params.txt').read_text());values.update(TimeMax='.00004',TimeBetSnapshot='.00004',MaxSizeTimestep=f'{cap:.17g}')
    if psutil.virtual_memory().available<(8*float(values['MaxMemSize'])/1024+4)*GIB:raise ValueError('RAM guard')
    binary=ROOT/f'GIZMO_{variant}_pair'
    if sha(binary)!=build['pinned_files'][binary.name]:raise ValueError('Binary changed')
    folder.mkdir();(folder/'output').mkdir();ic_hash=generate(folder,3,mode,p)
    original_ic,_=read(old/'ics.hdf5');ic,_=read(folder/'ics.hdf5')
    if set(ic)!=set(original_ic) or any(not np.array_equal(ic[k],original_ic[k]) for k in ic):raise ValueError('Diagnostic IC differs')
    param=folder/'params.txt';param.write_text(''.join(f'{k:32s} {v}\n' for k,v in values.items()))
    input_hash=sha(param);command=['mpirun','--bind-to','core','-np','8',str(binary),'params.txt']
    start=time.monotonic();peak=0
    record=dict(variant=variant,mode=mode,max_timestep=cap,directory=str(folder),command=command,physics=p,
                binary_sha256=sha(binary),input_sha256=input_hash,ic_sha256=ic_hash,status='running')
    save(folder/'result.json',record)
    with (folder/'run.log').open('x') as log:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                              env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(c.memory_info().rss for c in handle.children(recursive=True)))
            except psutil.NoSuchProcess:pass
            if time.monotonic()-start>180:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                record.update(status='timeout_raw_preserved');save(folder/'result.json',record);raise RuntimeError('Diagnostic timed out')
            try:proc.wait(timeout=.25)
            except subprocess.TimeoutExpired:pass
    record.update(returncode=proc.returncode,wall_seconds=time.monotonic()-start,peak_child_rss_gib=peak/GIB)
    save(folder/'result.json',record)
    if proc.returncode:record['status']='failed_raw_preserved';save(folder/'result.json',record);raise RuntimeError('Native diagnostic failed')
    paths=snapshots(folder/'output');a,t=native(paths[0],p,variant);last,tl=native(paths[-1],p,variant)
    times=[native(path,p,variant)[1] for path in paths]
    if len(paths)<2 or t!=0 or abs(tl-.00004)>1e-12 or any(y<x for x,y in zip(times,times[1:])):
        raise ValueError('Unexpected native time coverage')
    original_native,_=native(snapshots(old/'output')[0],p,variant)
    for k in ('Coordinates','Masses','ParticleIDs','InternalEnergy','Density','SmoothingLength'):
        if not np.array_equal(a[k],original_native[k]):raise ValueError('Diagnostic nonvelocity native state changed '+k)
    if sha(param)!=input_hash or sha(folder/'ics.hdf5')!=ic_hash:raise ValueError('Diagnostic input changed')
    record.update(status='collected_pending_scaling_check',native_times=times,snapshots=[str(x) for x in paths])
    save(folder/'result.json',record);return record

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    allow_existing=sys.argv[1:]==['--continue-collected']
    if sys.argv[1:] and not allow_existing:raise ValueError('Only --continue-collected is supported')
    base=ROOT/'snapshot_timing_audit_v2'
    if base.exists() and not allow_existing:raise ValueError('Existing audit requires explicit collection continuation')
    base.mkdir(exist_ok=allow_existing)
    report=dict(status='running',source_evidence={},diagnostics=[],scaling_checks=[])
    for name in ('run.c','kicks.c','io.c','init.c'):
        src=Path('/home/kaan/codes/gizmo')/name;dest=base/name
        if dest.exists():
            if not allow_existing or sha(dest)!=sha(src):raise ValueError('Source evidence changed')
        else:shutil.copy2(src,dest)
        report['source_evidence'][name]=dict(path=str(dest),sha256=sha(dest))
    try:
        for variant in ('mfm','mfv'):
            for mode in (0,1):
                cases=[]
                for cap in (1e-5,5e-6):
                    cases.append(run_diagnostic(variant,mode,cap,base,allow_existing));report['diagnostics'].append(cases[-1]);save(base/'report.json',report)
                ic,_=read(Path(cases[0]['directory'])/'ics.hdf5')
                arrays=[read(Path(c['snapshots'][0]))[0]['Velocities'] for c in cases]
                report['scaling_checks'].append(dict(variant=variant,mode=mode,checks=scaling_check(ic['Velocities'],*arrays)))
        report.update(status='passed',conclusion='Native t=0 Velocities are staggered after the first kick. Halving diagnostic timestep halves the velocity offset; zero-step extrapolation recovers input within float32 rounding. No native output has been retimed or corrected.',
                      scope='Output-timing validation only, not a full control or validation of historical velocity diagnostics.',script_sha256=sha(__file__))
    except Exception as e:report.update(status='needs_review',error=str(e));raise
    finally:save(base/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='diagnostics'},indent=2))

if __name__=='__main__':main()
