"""Isolated native MFM L4 validation and guarded full pair. No MFV/L5 admission.

Retains all native output. Original per-level numerics stay fixed; only tiny
explicit output-timing diagnostics use a reduced timestep cap. No auto-resume.
"""
import argparse,fcntl,json,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import psutil
BASE=Path('/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1')
sys.path.insert(0,str(BASE))
from smoke_gizmo import ROOT,sha,save,physics,params,read,generate,require_storage,storage_snapshot,GIB
from verify_gizmo import native,snapshots,sums,yt_check
from audit_snapshot_timing import scaling_check
from run_full_l3 import check_times,restart_files

LEVEL=4
NATIVE_COUNT=128*64*64
VALIDATION=ROOT/'validation_mfm_l4_v1'
FULL=ROOT/'full_mfm_l4_v1'
NONVELOCITY=('Coordinates','Masses','ParticleIDs','InternalEnergy','Density','SmoothingLength')

def dependencies(require_bundle=True):
    bundle=json.loads((BASE/'bundle.json').read_text())
    for name,digest in bundle['files'].items():
        if sha(BASE/name)!=digest:raise ValueError('Frozen L3 helper differs '+name)
    for name,evidence in bundle['native_scheduler_evidence'].items():
        if sha(evidence['path'])!=evidence['sha256']:raise ValueError('Native scheduler evidence differs '+name)
    build=json.loads((ROOT/'build.json').read_text())
    for name,digest in build['pinned_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Native input/evidence differs '+name)
    own=Path(__file__).parent/'bundle.json'
    if require_bundle:
        record=json.loads(own.read_text())
        if record['base_bundle_sha256']!=sha(BASE/'bundle.json') or record['build_sha256']!=sha(ROOT/'build.json'):
            raise ValueError('Bundle provenance differs')
        for name,digest in record['files'].items():
            if sha(own.parent/name)!=digest:raise ValueError('L4 frozen runner differs '+name)
    return build

def input_values(role,cap=None):
    if role not in ('smoke','timing','full'):raise ValueError('Unknown run role')
    if (role=='timing')!=(cap is not None) or (cap is not None and cap not in (1e-5,5e-6)):
        raise ValueError('Diagnostic timestep cannot leak into production')
    build=json.loads((ROOT/'build.json').read_text());template=ROOT/'params_mfm_L4.txt'
    if sha(template)!=build['pinned_files'][template.name]:raise ValueError('Native L4 template changed')
    values=params(template.read_text());p=physics()
    fixed={'MaxMemSize':1500,'PartAllocFactor':2.5,'MaxSizeTimestep':.05,'MinSizeTimestep':1e-12,
        'CpuTimeBetRestartFile':3600,'TimeLimitCPU':604800,'MinGasTemp':0,'InitGasTemp':0,
        'TimeBegin':0,'TimeOfFirstSnapshot':0,'OutputListOn':0,'NumFilesPerSnapshot':1,
        'NumFilesWrittenInParallel':1,'ICFormat':3,'SnapFormat':3,'BoxSize':10,'DesNumNgb':32}
    fixed.update({f'Softening_Type{i}':.15625 for i in range(6)})
    if any(float(values[k])!=v for k,v in fixed.items()):raise ValueError('Unreviewed native L4 setting')
    if any(values[k]!=v for k,v in {'InitCondFile':'ics','OutputDir':'output','RestartFile':'restart','SnapshotFileBase':'snapshot'}.items()):
        raise ValueError('Unexpected native output path')
    end={'smoke':.1,'timing':4e-5,'full':p['t_end_over_tcc']*p['t_cc']}[role]
    cadence=p['output_dt_over_tcc']*p['t_cc'] if role=='full' else end
    values.update(TimeMax=repr(end),TimeBetSnapshot=repr(cadence))
    if cap is not None:values['MaxSizeTimestep']=repr(cap)
    return values

def guard(required):
    snap=storage_snapshot(ROOT);require_storage(snap,required)
    if psutil.virtual_memory().available<(8*1500/1024+4)*GIB:raise RuntimeError('L4 native allocation plus 4GiB RAM reserve unavailable')
    return snap

def prepare(folder,mode,role,case_bytes,cap=None):
    if mode not in (0,1):raise ValueError('Invalid velocity law')
    if folder.exists():raise ValueError('Existing native directory cannot be reused')
    build=dependencies();values=input_values(role,cap);p=physics();preflight=guard(case_bytes)
    folder.mkdir(parents=True);(folder/'output').mkdir()
    digest=generate(folder,LEVEL,mode,p)
    (folder/'params.txt').write_text(''.join(f'{k:32s} {v}\n' for k,v in values.items()))
    record=dict(status='prepared',variant='mfm',mode=mode,level=LEVEL,role=role,max_timestep=float(values['MaxSizeTimestep']),
        t_end=float(values['TimeMax']),directory=str(folder),physics=p,input_sha256=sha(folder/'params.txt'),ic_sha256=digest,
        binary_sha256=build['pinned_files']['GIZMO_mfm_pair'],launcher_sha256=sha(__file__),case_bytes=case_bytes,
        storage_preflight=preflight)
    save(folder/'result.json',record);return record

def exact_nonvelocity(a,b,keys=None):
    if set(a)!=set(b):raise ValueError('Paired schemas differ')
    for key in (keys if keys is not None else [k for k in a if k!='Velocities']):
        if not np.array_equal(a[key],b[key]):raise ValueError('Nonvelocity paired field differs '+key)

def execute(case):
    dependencies();folder=Path(case['directory']);guard(case['case_bytes'])
    for name,key in (('params.txt','input_sha256'),('ics.hdf5','ic_sha256')):
        if sha(folder/name)!=case[key]:raise ValueError('Prepared input changed')
    binary=ROOT/'GIZMO_mfm_pair'
    if sha(binary)!=case['binary_sha256']:raise ValueError('Native executable changed')
    command=['mpirun','--bind-to','core','-np','8',str(binary),'params.txt']
    limit=6000 if case['role']=='full' else 180
    case.update(status='running',command=command,started_unix=time.time(),wall_limit_seconds=limit)
    save(folder/'result.json',case);save(ROOT/'current_mfm_l4.json',case)
    print('START '+str(folder),flush=True)
    start=time.monotonic();last_storage=start;peak=0;stop_reason=None;stop_at=None;previous={};previous_sample=start
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid);case['mpi_pid']=proc.pid;save(ROOT/'current_mfm_l4.json',case)
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
            resources.write(json.dumps(dict(unix=time.time(),elapsed_seconds=now-start,child_rss_bytes=rss,
                busy_cpu_cores=busy,guest_available_ram_bytes=memory.available,stop_reason=stop_reason))+'\n');resources.flush()
            previous,previous_sample=cpu,now
            if not stop_reason:
                if now-start>=limit:stop_reason='Bounded native runtime reached'
                elif memory.available<2*GIB:stop_reason='Guest available RAM below 2GiB'
                elif now-last_storage>=30:
                    try:require_storage(storage_snapshot(ROOT),0)
                    except Exception as exc:stop_reason='Storage guard: '+str(exc)
                    last_storage=now
                if stop_reason:
                    stop_at=now
                    with (folder/'output'/'stop').open('x') as marker:marker.write('Guard requests native checkpoint and stop.\n')
            if stop_at is not None and now-stop_at>60:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=2 if case['role']=='full' else .25)
            except subprocess.TimeoutExpired:pass
    case.update(status='native_finished_pending_validation',returncode=proc.returncode,wall_seconds=time.monotonic()-start,
        peak_child_rss_gib=peak/GIB,stop_reason=stop_reason);save(folder/'result.json',case);save(ROOT/'current_mfm_l4.json',case)
    if proc.returncode or stop_reason:raise RuntimeError('Native run failed/stopped; raw retained, no auto-resume')
    log=(folder/'run.log').read_text();expected=json.loads((ROOT/'build.json').read_text())['expected_config']['mfm']
    if any(flag not in log for flag in expected) or 'HYDRO_MESHLESS_FINITE_VOLUME' in log or 'Simulation ends.' not in log or 'Final time=' not in log:
        raise ValueError('Native method/terminal marker missing')
    return case

def collect(case):
    folder=Path(case['directory']);p=case['physics'];rows=[]
    if sha(folder/'params.txt')!=case['input_sha256'] or sha(folder/'ics.hdf5')!=case['ic_sha256']:
        raise ValueError('Native inputs changed during run')
    for path in snapshots(folder/'output'):
        digest=sha(path);a,t=native(path,p,'mfm')
        if len(a['Masses'])!=NATIVE_COUNT:raise ValueError('Wrong native L4 element count')
        independent=yt_check(path,p,'mfm');mass=sums(a,p)
        if sha(path)!=digest:raise ValueError('Native snapshot changed')
        rows.append(dict(snapshot=str(path),sha256=digest,time_code=t,t_over_tcc=t/p['t_cc'],elements=len(a['Masses']),
            bytes=path.stat().st_size,independent_relative_errors=independent,**mass))
    times=[r['time_code'] for r in rows]
    if len(rows)<2 or times[0]!=0 or any(y<x for x,y in zip(times,times[1:])) or abs(times[-1]-case['t_end'])>1e-10:
        raise ValueError('Native initial/evolved time coverage differs')
    if case['role']=='full':case['cadence']=check_times(times,p)
    if rows[0]['dense_mass']<=0:raise ValueError('Empty initial dense mass')
    for row in rows:row['dense_mass_over_initial']=row['dense_mass']/rows[0]['dense_mass']
    restarts=[dict(path=str(x),bytes=x.stat().st_size,sha256=sha(x)) for x in restart_files(folder)]
    case.update(series=rows,restart_files=restarts,independent_max_relative_mass_error=max(e for r in rows for e in r['independent_relative_errors'].values()))
    return case

def initial_fields(case):
    folder=Path(case['directory']);ic,t0=read(folder/'ics.hdf5');d,t=native(Path(case['series'][0]['snapshot']),case['physics'],'mfm')
    if t0!=0 or t!=0:raise ValueError('Missing initial time')
    for key in ('Coordinates','Masses','ParticleIDs','InternalEnergy'):
        if not np.array_equal(ic[key],d[key]):raise ValueError('Native initial recovery differs '+key)
    rho=ic['Masses'].astype(float)/.15625**3
    pressure=(case['physics']['gamma']-1)*d['Density'].astype(float)*d['InternalEnergy']
    return ic,d,dict(native_density_vs_lattice_max_relative=float(np.max(abs(d['Density']-rho)/rho)),
        native_pressure_vs_uniform_max_absolute=float(np.max(abs(pressure-case['physics']['p_wind']))),
        native_t0_velocity_max_offset=float(np.max(abs(d['Velocities'].astype(float)-ic['Velocities']))))

def timing_proof(case,report):
    if case['level']!=4 or case['variant']!='mfm' or report['status']!='passed':raise ValueError('Wrong timing evidence scope')
    ic,d,initial=initial_fields(case);velocity=[]
    tests=sorted([c for c in report['diagnostics'] if c['mode']==case['mode']],key=lambda c:c['max_timestep'],reverse=True)
    if [c['max_timestep'] for c in tests]!=[1e-5,5e-6]:raise ValueError('Missing L4 timestep-scaling tests')
    for test in tests:
        tf=Path(test['directory'])
        if test['level']!=4 or test['binary_sha256']!=case['binary_sha256'] or sha(tf/'params.txt')!=test['input_sha256'] or sha(tf/'ics.hdf5')!=test['ic_sha256']:
            raise ValueError('L4 timing provenance differs')
        tic,td,_=initial_fields(test)
        if set(ic)!=set(tic) or any(not np.array_equal(ic[k],tic[k]) for k in ic):raise ValueError('Timing ICs differ')
        exact_nonvelocity(d,td)
        if sha(test['series'][0]['snapshot'])!=test['series'][0]['sha256']:raise ValueError('Timing native state changed')
        velocity.append(td['Velocities'])
    initial['timing_scaling']=scaling_check(ic['Velocities'],*velocity)
    return initial

def measured_budget(smokes):
    if len(smokes)!=2 or {c['mode'] for c in smokes}!={0,1}:raise ValueError('Two L4 smokes required')
    if any(c['level']!=4 or c['variant']!='mfm' or c['role']!='smoke' for c in smokes):raise ValueError('Wrong budget baseline')
    snap=max(r['bytes'] for c in smokes for r in c['series'])
    restart=max(sum(r['bytes'] for r in c['restart_files']) for c in smokes)
    ic=max((Path(c['directory'])/'ics.hdf5').stat().st_size for c in smokes)
    size=int(1.15*(104*snap+3*restart+ic+256*1024**2))
    return dict(case_bytes=size,pair_bytes=2*size,snapshot_bytes=snap,restart_bytes=restart,ic_bytes=ic,
        method='104 native snapshots + two retained restart sets with 50% margin + IC +256MiB logs, all with15% margin. Separate10GiB free reserve. Runtime bounded6000+60s; original3600s restart interval.')

def validate():
    if VALIDATION.exists():raise ValueError('Existing L4 validation requires review, not a relaunch')
    dependencies();guard(6*GIB);VALIDATION.mkdir()
    report=dict(status='running',level=4,variant='mfm',smokes=[],diagnostics=[],script_sha256=sha(__file__))
    try:
        for mode in (0,1):
            smoke=prepare(VALIDATION/f'smoke_{mode}',mode,'smoke',GIB);execute(smoke);collect(smoke)
            smoke['status']='native_checked';save(Path(smoke['directory'])/'result.json',smoke)
            report['smokes'].append(smoke);save(VALIDATION/'report.json',report)
            for cap in (1e-5,5e-6):
                test=prepare(VALIDATION/f'timing_{mode}_{cap:g}',mode,'timing',GIB,cap);execute(test);collect(test)
                test['status']='native_checked';save(Path(test['directory'])/'result.json',test)
                report['diagnostics'].append(test);save(VALIDATION/'report.json',report)
        a,b=(initial_fields(c) for c in report['smokes'])
        exact_nonvelocity(a[0],b[0]);exact_nonvelocity(a[1],b[1])
        if report['smokes'][0]['input_sha256']!=report['smokes'][1]['input_sha256']:raise ValueError('Paired native parameters differ')
        report['status']='passed'
        report['initial_checks']=[timing_proof(c,report) for c in report['smokes']]
        report['budget']=measured_budget(report['smokes']);report['full_pair_storage_check']=guard(report['budget']['pair_bytes'])
        report['scope']='MFM L4 setup/output-timing and short evolved native validation, not full science controls. No native values changed.'
    except Exception as exc:report.update(status='needs_review',error=str(exc));raise
    finally:save(VALIDATION/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('smokes','diagnostics')},indent=2),flush=True)

def full_pair():
    if FULL.exists():raise ValueError('Existing full pair must never be restarted blindly')
    dependencies();path=VALIDATION/'report.json';proof=json.loads(path.read_text())
    if proof['status']!='passed' or proof['script_sha256']!=sha(__file__):raise ValueError('L4 validation not current')
    for case in proof['smokes']+proof['diagnostics']:
        folder=Path(case['directory'])
        if sha(folder/'params.txt')!=case['input_sha256'] or sha(folder/'ics.hdf5')!=case['ic_sha256']:raise ValueError('Validation input differs')
        for row in case['series']:
            if sha(row['snapshot'])!=row['sha256']:raise ValueError('Validation raw differs')
    for case in proof['smokes']:timing_proof(case,proof)
    budget=measured_budget(proof['smokes'])
    if budget!=proof['budget']:raise ValueError('L4 measured budget changed')
    snap=guard(budget['pair_bytes']);FULL.mkdir()
    batch=dict(status='preparing',level=4,variant='mfm',validation_sha256=sha(path),budget=budget,storage_preflight=snap,finished=[],script_sha256=sha(__file__))
    try:
        cases=[prepare(FULL/('sharp13' if mode==0 else 'tanh13'),mode,'full',budget['case_bytes']) for mode in (0,1)]
        exact_nonvelocity(*[read(Path(c['directory'])/'ics.hdf5')[0] for c in cases])
        if cases[0]['input_sha256']!=cases[1]['input_sha256']:raise ValueError('Full pair parameters differ')
        batch.update(status='running',planned=cases);save(FULL/'batch.json',batch)
        for case in cases:
            if sha(path)!=batch['validation_sha256']:raise ValueError('L4 proof changed mid-pair')
            execute(case);collect(case);case['initial_checks']=timing_proof(case,proof)
            case['status']='complete_independent_checks';save(Path(case['directory'])/'result.json',case)
            save(ROOT/'current_mfm_l4.json',case)
            batch['finished'].append(case);save(FULL/'batch.json',batch)
            print(f'FINISH mode={case["mode"]}: {len(case["series"])} native states, {case["wall_seconds"]:.1f}s, peak RSS{case["peak_child_rss_gib"]:.3f}GiB',flush=True)
        if cases[0]['series'][0]['dense_mass']!=cases[1]['series'][0]['dense_mass']:raise ValueError('Initial dense denominators differ')
        exact_nonvelocity(initial_fields(cases[0])[1],initial_fields(cases[1])[1])
        batch.update(status='complete_independent_checks',next_gate='Analyze under a new directory and overlay MFM L3/L4. MFV and L5 remain excluded.')
    except Exception as exc:batch.update(status='needs_review',error=str(exc));raise
    finally:save(FULL/'batch.json',batch)

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--validate',action='store_true');group.add_argument('--run',action='store_true');args=parser.parse_args()
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    validate() if args.validate else full_pair()

if __name__=='__main__':main()
