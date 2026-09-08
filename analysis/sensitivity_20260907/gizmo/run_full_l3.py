"""Guarded native GIZMO L3 sensitivity pairs. No L4/L5 admission in this runner.

Original production numerics are unchanged. Only exact metadata-derived output
times replace rounded historical values. Native raw and all extra outputs stay.
"""
import argparse,fcntl,json,os,signal,subprocess,time
from pathlib import Path
import numpy as np
import psutil
import verify_gizmo as verification
from smoke_gizmo import ROOT,sha,save,physics,params,generate,read,require_storage,storage_snapshot,GIB
from verify_gizmo import native,snapshots,sums,initial,pair,yt_check

LEVEL=3
WALL_LIMIT=6000
STOP_GRACE=60
TIME_TOL=10/(1<<29)  # two ticks of the native 29-bit timeline, in t/t_cc
MODULES=('run_full_l3.py','setup_gizmo.py','smoke_gizmo.py','verify_gizmo.py','audit_snapshot_timing.py')

def input_for(variant,level=LEVEL):
    if variant not in ('mfm','mfv') or level!=LEVEL:raise ValueError('Only validated L3 MFM/MFV is admitted')
    build=json.loads((ROOT/'build.json').read_text());template=ROOT/f'params_{variant}_L{level}.txt'
    if sha(template)!=build['pinned_files'][template.name]:raise ValueError('Pinned parameter template changed')
    p=physics();values=params(template.read_text())
    fixed={'ICFormat':3,'SnapFormat':3,'OutputListOn':0,'NumFilesPerSnapshot':1,
           'NumFilesWrittenInParallel':1,'TimeOfFirstSnapshot':0,'TimeBegin':0,
           'ComovingIntegrationOn':0,'BoxSize':10,'CpuTimeBetRestartFile':3600,
           'TimeLimitCPU':604800,'MaxSizeTimestep':.05,'MinSizeTimestep':1e-12,
           'PartAllocFactor':2.5,'MaxMemSize':1000,'InitGasTemp':0,'MinGasTemp':0}
    for key,value in fixed.items():
        if float(values[key])!=value:raise ValueError('Unreviewed native setting '+key)
    for key,value in {'InitCondFile':'ics','OutputDir':'output','RestartFile':'restart','SnapshotFileBase':'snapshot'}.items():
        if values[key]!=value:raise ValueError('Unreviewed native path '+key)
    values.update(TimeMax=repr(p['t_end_over_tcc']*p['t_cc']),TimeBetSnapshot=repr(p['output_dt_over_tcc']*p['t_cc']))
    return ''.join(f'{key:32s} {value}\n' for key,value in values.items())

def check_times(times,p):
    t=np.asarray(times,dtype=float)/p['t_cc']
    if len(t)<101 or len(t)>103 or not np.all(np.isfinite(t)) or t[0]!=0 or np.any(np.diff(t)<0):
        raise ValueError('Missing or invalid native output times')
    if abs(t[-1]-5)>TIME_TOL or any(np.min(abs(t-target))>TIME_TOL for target in np.linspace(0,5,101)):
        raise ValueError('Incomplete native 0:0.05:5 cadence')
    return dict(native_snapshots=len(t),distinct_header_times=len(np.unique(t)),
        repeated_header_times=[float(x) for x,c in zip(*np.unique(t,return_counts=True)) if c>1],
        policy='All files and original times retained, including extra or exactly equal terminal headers. No retiming, thinning or synthesized states.')

def restart_files(folder):
    root=folder/'output'/'restartfiles';paths=list(root.glob('*'))
    expected={f'restart.{i}' for i in range(8)}
    names={x.name for x in paths if x.is_file()}
    if not expected<=names or names-expected-{x+'.bak' for x in expected}:
        raise ValueError('Incomplete or unexpected native restart set')
    backup={x for x in names if x.endswith('.bak')}
    if backup and backup!={x+'.bak' for x in expected}:raise ValueError('Partial backup restart set')
    if any(x.stat().st_size==0 for x in paths):raise ValueError('Empty native restart file')
    return paths

def budget(variant):
    batch=json.loads((ROOT/'smoke_batch.json').read_text())
    cases=[c for c in batch['finished'] if c['variant']==variant]
    if {c['mode'] for c in cases}!={0,1}:raise ValueError('Both measured smokes required')
    snap_bytes=max(Path(r['snapshot']).stat().st_size for c in cases for r in c['outputs'])
    restart_bytes=max(sum(x.stat().st_size for x in restart_files(Path(c['directory']))) for c in cases)
    ic_bytes=max((Path(c['directory'])/'ics.hdf5').stat().st_size for c in cases)
    # At most one periodic restart before the 6000-second limit, then final/stop
    # restart. Native .bak rotation retains both. Add 50% restart margin, three
    # extra snapshot slots, 256MiB logs and 15% overall allowance; delete nothing.
    total=int(1.15*(104*snap_bytes+3*restart_bytes+ic_bytes+256*1024**2))
    return dict(case_bytes=total,pair_bytes=2*total,snapshot_bytes=snap_bytes,
                measured_restart_set_bytes=restart_bytes,ic_bytes=ic_bytes,
                method='104 native snapshots + two restart sets with 50% margin + IC + 256MiB logs; 15% overall margin. Separate 10GiB free-space reserve.')

def preflight():
    proof=json.loads((ROOT/'verification.json').read_text());build=json.loads((ROOT/'build.json').read_text())
    if proof['status']!='passed' or len(proof['independent_checks'])!=8 or len(proof['pairs'])!=2:
        raise ValueError('Incomplete native/independent L3 verification')
    if proof['script_sha256']!=sha(verification.__file__) or proof['smoke_sha256']!=sha(ROOT/'smoke_batch.json'):
        raise ValueError('Verification provenance changed')
    for name,digest in build['pinned_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Pinned file changed '+name)
    for v in ('mfm','mfv'):input_for(v)
    p=physics();snap=storage_snapshot(ROOT);budgets={v:budget(v) for v in ('mfm','mfv')}
    require_storage(snap,sum(b['pair_bytes'] for b in budgets.values()))
    if psutil.virtual_memory().available<(8*1000/1024+4)*GIB:raise RuntimeError('Native allocation plus 4GiB RAM reserve unavailable')
    return dict(physics=p,storage=snap,budgets=budgets,planned_controls=4,levels=[3],
        wall_limit_seconds=WALL_LIMIT,stop_grace_seconds=STOP_GRACE,
        scope='Native MFM/MFV L3 historical/sharp only; L4/L5 are not enabled.',
        dependencies={name:sha(Path(__file__).parent/name) for name in MODULES},
        verification_sha256=sha(ROOT/'verification.json'),build_sha256=sha(ROOT/'build.json'))

def check_dependencies(plan):
    if any(sha(Path(__file__).parent/name)!=digest for name,digest in plan['dependencies'].items()):
        raise ValueError('Frozen runner dependency changed')
    if sha(ROOT/'verification.json')!=plan['verification_sha256'] or sha(ROOT/'build.json')!=plan['build_sha256']:
        raise ValueError('Setup/verification ledger changed')

def prepare_pair(variant,plan):
    check_dependencies(plan);require_storage(storage_snapshot(ROOT),plan['budgets'][variant]['pair_bytes'])
    p=physics();text=input_for(variant);cases=[];build=json.loads((ROOT/'build.json').read_text())
    folders=[ROOT/'runs'/f'L3_{variant}_{"tanh13" if m else "sharp13"}' for m in (0,1)]
    if any(f.exists() for f in folders):raise ValueError('Existing case requires review, never overwrite or blind-resume')
    for mode,folder in enumerate(folders):
        folder.mkdir(parents=True);(folder/'output').mkdir();param=folder/'params.txt';param.write_text(text)
        ic_hash=generate(folder,LEVEL,mode,p)
        case=dict(status='prepared',variant=variant,mode=mode,level=LEVEL,directory=str(folder),physics=p,
            input_sha256=sha(param),ic_sha256=ic_hash,binary_sha256=build['pinned_files'][f'GIZMO_{variant}_pair'],
            launcher_sha256=sha(__file__),budget=plan['budgets'][variant])
        save(folder/'result.json',case);cases.append(case)
    arrays=[read(f/'ics.hdf5')[0] for f in folders]
    if set(arrays[0])!=set(arrays[1]):raise ValueError('Paired IC schemas differ')
    for key in arrays[0]:
        if key!='Velocities' and not np.array_equal(arrays[0][key],arrays[1][key]):raise ValueError('Nonvelocity IC changed '+key)
    return cases

def collect(case):
    folder=Path(case['directory']);p=case['physics'];rows=[]
    if sha(folder/'params.txt')!=case['input_sha256'] or sha(folder/'ics.hdf5')!=case['ic_sha256']:
        raise ValueError('Run input changed')
    for path in snapshots(folder/'output'):
        before=sha(path);a,t=native(path,p,case['variant']);mass=sums(a,p)
        if len(a['Masses'])!=65536:raise ValueError('Native element count changed')
        checks=yt_check(path,p,case['variant'])
        if sha(path)!=before:raise ValueError('Native snapshot changed while checking')
        rows.append(dict(snapshot=str(path),sha256=before,time_code=t,t_over_tcc=t/p['t_cc'],
            elements=len(a['Masses']),bytes=path.stat().st_size,independent_relative_errors=checks,**mass))
    cadence=check_times([r['time_code'] for r in rows],p)
    initial_checks=initial(case)
    if rows[0]['dense_mass']<=0:raise ValueError('Empty initial dense-mass denominator')
    for r in rows:r['dense_mass_over_initial']=r['dense_mass']/rows[0]['dense_mass']
    restarts=[dict(path=str(x),bytes=x.stat().st_size,sha256=sha(x)) for x in restart_files(folder)]
    return dict(series=rows,cadence=cadence,initial_checks=initial_checks,restart_files=restarts,
        independent_max_relative_mass_error=max(e for r in rows for e in r['independent_relative_errors'].values()))

def run_case(case,plan):
    check_dependencies(plan);folder=Path(case['directory']);p=case['physics'];variant=case['variant']
    required=case['budget']['case_bytes'];case['storage_preflight']=storage_snapshot(ROOT);require_storage(case['storage_preflight'],required)
    if psutil.virtual_memory().available<(8*1000/1024+4)*GIB:raise RuntimeError('RAM guard')
    binary=ROOT/f'GIZMO_{variant}_pair'
    if sha(binary)!=case['binary_sha256']:raise ValueError('Pinned executable changed')
    command=['mpirun','--bind-to','core','-np','8',str(binary),'params.txt']
    case.update(status='running',command=command,started_unix=time.time());save(folder/'result.json',case);save(ROOT/'current_full_l3.json',case)
    print('START '+str(folder),flush=True)
    start=time.monotonic();last_storage=start;peak=0;stop_reason=None;stop_at=None;previous={};previous_sample=start
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                              env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid);case['mpi_pid']=proc.pid;save(ROOT/'current_full_l3.json',case)
        while proc.poll() is None:
            now=time.monotonic();memory=psutil.virtual_memory();cpu={};rss=0
            try:
                for child in handle.children(recursive=True):
                    try:
                        rss+=child.memory_info().rss;ct=child.cpu_times();cpu[child.pid]=ct.user+ct.system
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            except psutil.NoSuchProcess:pass
            peak=max(peak,rss)
            busy=sum(max(0,c-previous[pid]) for pid,c in cpu.items() if pid in previous)/max(now-previous_sample,1e-6)
            resources.write(json.dumps(dict(unix=time.time(),elapsed_seconds=now-start,child_rss_bytes=rss,peak_child_rss_bytes=peak,
                busy_cpu_cores=busy,guest_available_ram_bytes=memory.available,stop_reason=stop_reason))+'\n');resources.flush()
            previous,previous_sample=cpu,now
            if not stop_reason:
                if now-start>=WALL_LIMIT:stop_reason='6000-second retention/runtime limit'
                elif memory.available<2*GIB:stop_reason='Guest available RAM below 2GiB'
                elif now-last_storage>=30:
                    try:require_storage(storage_snapshot(ROOT),0)
                    except Exception as exc:stop_reason='Storage guard: '+str(exc)
                    last_storage=now
                if stop_reason:
                    stop_at=now
                    with (folder/'output'/'stop').open('x') as marker:marker.write('Guarded study requests native checkpoint and stop.\n')
                    case.update(status='checkpoint_stop_requested',stop_reason=stop_reason);save(ROOT/'current_full_l3.json',case)
            if stop_at is not None and now-stop_at>STOP_GRACE:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:pass
    case.update(status='needs_review',returncode=proc.returncode,wall_seconds=time.monotonic()-start,
                peak_child_rss_gib=peak/GIB,stop_reason=stop_reason);save(folder/'result.json',case)
    if proc.returncode or stop_reason:raise RuntimeError('Native run failed/stopped; all partial data retained, no automatic resume')
    log=(folder/'run.log').read_text();expected=json.loads((ROOT/'build.json').read_text())['expected_config'][variant]
    if any(flag not in log for flag in expected) or 'Final time=' not in log or 'Simulation ends.' not in log:
        raise ValueError('Native method or terminal completion not confirmed')
    case.update(status='validating');save(ROOT/'current_full_l3.json',case)
    case.update(collect(case));case['status']='complete_independent_checks';save(folder/'result.json',case);save(ROOT/'current_full_l3.json',case)
    print(f'FINISH {variant} mode={case["mode"]}: {case["cadence"]["native_snapshots"]} native states, {case["wall_seconds"]:.1f}s, peak RSS {case["peak_child_rss_gib"]:.3f}GiB',flush=True)
    return case

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args();locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    plan=preflight()
    if not args.run:print(json.dumps(plan,indent=2));return
    path=ROOT/'full_l3_batch.json'
    if path.exists():raise ValueError('Existing batch requires review, not rerunning')
    batch=dict(status='running',pid=os.getpid(),plan=plan,finished=[],pairs=[])
    try:
        for variant in ('mfm','mfv'):
            cases=prepare_pair(variant,plan)
            for c in cases:batch['finished'].append(run_case(c,plan));save(path,batch)
            if cases[0]['series'][0]['dense_mass']!=cases[1]['series'][0]['dense_mass']:raise ValueError('Paired initial denominator differs')
            batch['pairs'].append(dict(variant=variant,level=3,checks=pair(*cases)));save(path,batch)
        batch.update(status='complete_independent_checks',next_gate='L4 separate native initial/timing/evolved checks and whole-pair retention budget. Not launched by this L3-only runner.')
    except Exception as exc:batch.update(status='stopped_needs_review',error=str(exc));raise
    finally:save(path,batch)

if __name__=='__main__':main()
