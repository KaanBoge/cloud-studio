"""New native L4 validation only. Existing L3 outputs and frozen runners untouched."""
import fcntl,json,math,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np,psutil
from yt.frontends.gadget.data_structures import GadgetHDF5Dataset
from yt.frontends.gadget.io import IOHandlerGadgetHDF5

sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4')
from gadget_controls import ROOT,NATIVE,sha,save,parameters,metadata,dependencies,generate,read,native_summary,CONFIG,EXPECTED_BINARY,storage_snapshot,require_storage,GIB
from native_cadence import expected_times,cadence

LEVEL=4
DIMS=(128,64,64)
COUNT=math.prod(DIMS)
DX=20/DIMS[0]
VALIDATION=ROOT/'validation_l4_v1'

def input_values(text,p,short=False):
    original=parameters(text)
    required={'MaxMemSize':2000,'MaxSizeTimestep':.05,'CourantFac':.15,'DesNumNgb':64,
        'MaxNumNgbDeviation':2,'MinEgySpec':0,'MinSizeTimestep':0,'CpuTimeBetRestartFile':7200}
    if any(float(original[k])!=v for k,v in required.items()):raise ValueError('Original native L4 settings changed')
    v=dict(original)
    v.update(InitCondFile='./ics',OutputDir='./output',TimeMax=format(5*p['t_cc'],'.17g'),
        TimeBetSnapshot=format(p['t_cc']/20,'.17g'),TimeBetStatistics=format(p['t_cc']/20,'.17g'))
    if short:v.update(TimeMax='0.1',TimeBetSnapshot='0.1')
    return v

def paired_nonvelocity(a,b):
    if set(a)!=set(b):raise ValueError('Pair schemas differ')
    for key in a:
        if key!='Velocities' and not np.array_equal(a[key],b[key]):raise ValueError('Nonvelocity pair differs: '+key)

def initial_checks(a,ic,p):
    if not np.array_equal(a['ParticleIDs'],ic['ParticleIDs']):raise ValueError('Native IDs changed')
    errors={}
    for key in ('Coordinates','Masses','InternalEnergy','Velocities'):
        expected=ic[key].astype(a[key].dtype)
        bound=float(4*np.finfo(a[key].dtype).eps*max(float(np.max(abs(expected))),1e-12))
        error=float(np.max(abs(a[key].astype(float)-expected.astype(float))))
        if error>bound:raise ValueError(f'Native initial {key} differs: {error} > {bound}')
        errors[key]=dict(max_absolute_error=error,storage_roundoff_bound=bound)
    nominal=ic['Masses']/DX**3
    return dict(level=LEVEL,dx=DX,native_vs_ic=errors,
        native_density_vs_lattice_max_relative=float(np.max(abs(a['Density']/nominal-1))),
        native_pressure_vs_uniform_max_absolute=float(np.max(abs(a['Pressure'].astype(float)-p['p_wind']))),
        native_pressure_min=float(a['Pressure'].min()),native_pressure_max=float(a['Pressure'].max()),
        scope='Only initial header velocity synchronization tested. Evolved mass diagnostics; no synchronized velocity claim.')

def independent(path,p):
    digest=sha(path)
    ds=GadgetHDF5Dataset(str(path),unit_base={'length':(1,'cm'),'mass':(1,'g'),'velocity':(1,'cm/s')},
        bounding_box=np.array([[0,20],[0,10],[0,10]],float))
    data=ds.all_data();mass=np.asarray(data['PartType0','Masses'].to_value('code_mass'),dtype=float)
    rho=np.asarray(data['PartType0','Density'].to_value('code_density'),dtype=float)
    ids=np.asarray(data['PartType0','ParticleIDs'])
    if ds.cosmological_simulation or len(mass)!=COUNT or sha(path)!=digest:raise ValueError('Independent L4 scope/count/raw mismatch')
    if not np.allclose(ds.domain_right_edge.to_value('code_length'),p['box'],rtol=0,atol=1e-12):raise ValueError('Independent domain mismatch')
    return dict(total_mass=float(mass.sum()),dense_mass=float(mass[rho>p['chi']*p['rho_wind']/3].sum()),
        tagged_mass=float(mass[ids>=p['cloud_id_start']].sum())),float(ds.current_time.to_value('code_time'))

def verify_rows(folder,p,ic,values):
    rows=[];initial=None;native_initial=None
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        a,row=native_summary(path,p)
        if len(a['Masses'])!=COUNT or not np.array_equal(a['ParticleIDs'],ic['ParticleIDs']):raise ValueError('Native L4 count/IDs changed')
        expected={'Coordinates','Density','InternalEnergy','Masses','Pressure','SmoothingLength','Velocities','ParticleIDs'}
        if set(a)!=expected or any(a[k].dtype!=np.dtype('uint32' if k=='ParticleIDs' else 'float32') for k in a):raise ValueError('Native field schema/storage changed')
        other,t=independent(path,p)
        errors={key:abs(value-row[key])/max(abs(row[key]),1e-12) for key,value in other.items()}
        if t!=row['time_code'] or max(errors.values())>1e-11:raise ValueError('Independent native time/mass mismatch')
        row['independent_relative_errors']=errors
        if initial is None:
            if t!=0:raise ValueError('Missing initial native snapshot')
            initial=initial_checks(a,ic,p);native_initial=a
        rows.append(row)
    times=np.array([row['time_code'] for row in rows]);expected,unit,block=expected_times(values)
    bound=8*np.finfo(float).eps*max(1,float(values['TimeMax']))
    if len(times)!=len(expected) or len(times)<2 or np.any(np.diff(times)<=0) or np.max(abs(times-expected))>bound:raise ValueError('Unexpected native output schedule; preserve all states')
    return rows,initial,native_initial,dict(native_count=len(times),max_exact_scheduler_error=float(np.max(abs(times-expected))),
        integer_time_unit_code=unit,native_output_block_code=block,roundoff_bound=bound,actual_times=times.tolist())

def measured_budget(cases):
    snap=max(r['bytes'] for c in cases for r in c['series'])
    restart=max(sum(r['bytes'] for r in c['retained_restarts']) for c in cases)
    ic=max((Path(c['directory'])/'ics.hdf5').stat().st_size for c in cases)
    per=math.ceil((104*snap+3*restart+ic+256*1024**2)*1.2)
    return dict(native_snapshot_bytes=snap,eight_rank_restart_bytes=restart,ic_bytes=ic,per_case_bytes=per,pair_bytes=2*per,
        formula='104 snapshots +3 measured eight-rank restart sets +IC +256MiB logs per case, then20% margin. Separate10GiB reserve on BOTH filesystems. Full-case external cap6000s below native7200s restart interval, no auto-resume.')

def request_stop(proc,folder):
    if proc.poll() is not None:return
    (folder/'output').mkdir(exist_ok=True);(folder/'output/stop').touch(exist_ok=False)
    try:proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=15)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)

def smoke(mode,p):
    dependencies();require_storage(storage_snapshot(ROOT),GIB)
    if psutil.virtual_memory().available<20*GIB:raise RuntimeError('Native L4 guarded RAM requires20GiB available')
    folder=VALIDATION/('tanh13' if mode else 'sharp13')
    folder.mkdir()  # no existing directory or resume
    ic=generate(folder,LEVEL,mode,p)
    values=input_values((ROOT/'params_L4.txt').read_text(),p,short=True)
    param=folder/'params.txt';param.write_text(''.join(f'{k:34s} {v}\n' for k,v in values.items()))
    command=['mpirun','--bind-to','core','-np','8',str(ROOT/'Gadget4_pair'),'params.txt']
    record=dict(status='running',level=LEVEL,mode=mode,physics=p,directory=str(folder),command=command,
        binary_sha256=EXPECTED_BINARY,input_sha256=sha(param),ic_sha256=sha(folder/'ics.hdf5'))
    save(folder/'result.json',record);print('START L4 validation '+str(folder),flush=True)
    start=time.monotonic();peak=0;guard=None;previous={};last_sample=start;last_guard=start
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid)
        try:
            while proc.poll() is None:
                now=time.monotonic();rss=0;delta=0;current={}
                try:
                    for child in handle.children(recursive=True):
                        try:
                            rss+=child.memory_info().rss;cpu=child.cpu_times();total=cpu.user+cpu.system;current[child.pid]=total
                            if child.pid in previous:delta+=max(0,total-previous[child.pid])
                        except psutil.NoSuchProcess:pass
                except psutil.NoSuchProcess:pass
                peak=max(peak,rss);available=psutil.virtual_memory().available
                resources.write(json.dumps(dict(elapsed_seconds=now-start,rss_bytes=rss,available_bytes=available,
                    busy_cpu_cores=delta/max(now-last_sample,1e-6)))+'\n');resources.flush();previous=current;last_sample=now
                if available<2*GIB or now-start>600:raise RuntimeError('Native L4 smoke RAM/runtime guard')
                if now-last_guard>30:require_storage(storage_snapshot(ROOT),0);last_guard=time.monotonic()
                try:proc.wait(timeout=.25)
                except subprocess.TimeoutExpired:pass
        except BaseException as exc:
            guard=repr(exc);request_stop(proc,folder)
            record.update(status='stopped_needs_review',error=guard,returncode=proc.returncode,wall_seconds=time.monotonic()-start,peak_child_rss_gib=peak/GIB)
            save(folder/'result.json',record);raise
    record.update(status='solver_finished_pending_validation',returncode=proc.returncode,wall_seconds=time.monotonic()-start,
        peak_child_rss_gib=peak/GIB,guard=guard);save(folder/'result.json',record)
    try:
        if proc.returncode:raise RuntimeError('Native L4 smoke failed')
        log=(folder/'run.log').read_text()
        if any(flag not in log for flag in CONFIG) or 'INIT: Hsml seed uses mean gas particle mass' not in log:raise ValueError('Native binary runtime evidence changed')
        rows,initial,a,schedule=verify_rows(folder,p,ic,values)
        restarts=list((folder/'output/restartfiles').glob('restart.*'))
        if len(restarts)!=8:raise ValueError('Native eight-rank restart set missing or unexpected extras')
        if sha(param)!=record['input_sha256'] or sha(folder/'ics.hdf5')!=record['ic_sha256']:raise ValueError('Inputs changed')
        record.update(status='passed_independent_L4_smoke',series=rows,initial=initial,cadence=schedule,
            retained_restarts=[dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path)) for path in sorted(restarts)])
        save(folder/'result.json',record)
    except Exception as exc:
        record.update(status='needs_review',error=str(exc));save(folder/'result.json',record);raise
    print(f"FINISH L4 validation mode={mode}: {len(rows)} states, {record['wall_seconds']:.2f}s, peak{peak/GIB:.3f}GiB",flush=True)
    return record

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    dependencies();bundle=json.loads((Path(__file__).parent/'bundle.json').read_text())
    for path,digest in bundle['pinned_files'].items():
        if sha(path)!=digest:raise ValueError('Frozen L4 validation dependency changed: '+path)
    if VALIDATION.exists():raise ValueError('Existing L4 validation must not be relaunched')
    if psutil.virtual_memory().available<20*GIB:raise RuntimeError('Insufficient native L4 preflight RAM')
    before=storage_snapshot(ROOT);require_storage(before,2*GIB);p=metadata();VALIDATION.mkdir()
    result=dict(status='running',level=LEVEL,grid=DIMS,elements=COUNT,physics=p,storage_before=before,cases=[],
        full_science_controls_completed=0,frozen_bundle_sha256=sha(Path(__file__).parent/'bundle.json'))
    save(VALIDATION/'report.json',result)
    try:
        for mode in (0,1):result['cases'].append(smoke(mode,p));save(VALIDATION/'report.json',result)
        a,b=result['cases']
        if a['input_sha256']!=b['input_sha256']:raise ValueError('Paired numerical input differs')
        ic0,_=read(Path(a['directory'])/'ics.hdf5');ic1,_=read(Path(b['directory'])/'ics.hdf5')
        paired_nonvelocity(ic0,ic1);paired_nonvelocity(read(a['series'][0]['snapshot'])[0],read(b['series'][0]['snapshot'])[0])
        legacy=NATIVE/'runs/G4_3D_L4_chi100/ics_L4_chi100.hdf5';old,_=read(legacy)
        if set(old)!=set(ic1) or any(not np.array_equal(old[k],ic1[k]) for k in old):raise ValueError('Archived law fails historical L4 IC reconstruction')
        values=input_values((ROOT/'params_L4.txt').read_text(),p);times,_,_=expected_times(values)
        budget=measured_budget(result['cases']);current=storage_snapshot(ROOT)
        try:require_storage(current,budget['pair_bytes']);gate=dict(passed=True)
        except RuntimeError as exc:gate=dict(passed=False,reason=str(exc))
        result.update(status='passed_L4_initial_and_short_evolved_mass_checks',native_output_count=sum(len(c['series']) for c in result['cases']),
            historical_IC_arrays_exactly_reproduced=True,original_ladder_ic_sha256=sha(legacy),nonvelocity_IC_and_native_initial_fields_exact=True,
            full_native_schedule_prediction=cadence(times,p,values),full_pair_budget=budget,full_pair_storage_gate=gate,
            storage_after=current,checker_sha256=sha(__file__),all_raw_retained=True,
            caveats=['Two short tests, not full101-state controls. No full L4 worker enabled here.',
                'Original native SPH kernel pressure variation and fully periodic boundaries retained identically; not a matched grid-code baseline.',
                'Initial velocity checked; evolved velocity-at-header-time synchronization not certified.',
                'yt sums raw particle fields without spatial reconstruction; rectangular bounds affect only reader geometry.',
                'All native timestamps and raw/IC/restart/log files retained unchanged.'])
    except Exception as exc:result.update(status='needs_review',error=str(exc));raise
    finally:save(VALIDATION/'report.json',result)
    print(json.dumps({k:result[k] for k in ('status','native_output_count','full_pair_budget','full_pair_storage_gate')},indent=2),flush=True)

if __name__=='__main__':main()
