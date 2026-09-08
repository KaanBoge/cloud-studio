"""Two native Gadget-4 L3 controls after verified native smokes; no auto-resume."""
import fcntl,json,math,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np,psutil
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4')
from gadget_controls import ROOT,sha,save,parameters,metadata,dependencies,generate,read,native_summary,CONFIG,EXPECTED_BINARY,storage_snapshot,require_storage,GIB
from verify_gadget import independent,initial_checks,paired_nonvelocity

def full_inputs(text,p):
    values=parameters(text)
    if (float(values['MaxMemSize']),float(values['MaxSizeTimestep']),float(values['CourantFac']),float(values['MinEgySpec']),float(values['CpuTimeBetRestartFile']))!=(1000,.05,.15,0,7200):raise ValueError('Native L3 numerical settings changed')
    values.update(InitCondFile='./ics',OutputDir='./output',TimeMax=format(5*p['t_cc'],'.17g'),
        TimeBetSnapshot=format(p['t_cc']/20,'.17g'),TimeBetStatistics=format(p['t_cc']/20,'.17g'))
    return values

def cadence(times,p,values):
    times=np.array(times,float);target=np.linspace(0,5*p['t_cc'],101)
    if len(times)<101 or times[0]!=0 or not np.all(np.isfinite(times)) or np.any(np.diff(times)<0):raise ValueError('Missing/nonmonotonic native times')
    # The original build writes only at top-level synchronized timesteps.
    # A scheduled time may therefore be delayed by at most MaxSizeTimestep.
    quantum=1e-10*p['t_cc'];delay=float(values['MaxSizeTimestep'])
    if len(times) not in (101,102):raise ValueError('Unexpected native count: retain files and review')
    for requested in target:
        if not np.any((times>=requested-quantum)&(times<=requested+delay+quantum)):raise ValueError('Missing scheduled output within native synchronization bound')
    if abs(times[-1]-target[-1])>quantum:raise ValueError('Incomplete native terminal interval')
    return dict(native_snapshots=len(times),distinct_header_times=len(np.unique(times)),scheduled_count=101,
        maximum_output_delay_code=delay,policy='Original synchronized-output build retained. All actual times, extra terminal files and equal-header states retained; no retiming or synthesized frames.')

def budget():
    smoke=ROOT/'smokes/L3_sharp13';snap=(smoke/'output/snapshot_000.hdf5').stat().st_size
    restarts=list((smoke/'output/restartfiles').glob('restart.*'))
    if len(restarts)!=8:raise ValueError('Native eight-rank restart set not measured')
    restart=sum(path.stat().st_size for path in restarts);ic=(smoke/'ics.hdf5').stat().st_size
    per=math.ceil((104*snap+3*restart+ic+256*1024**2)*1.2)
    return dict(native_snapshot_bytes=snap,eight_rank_restart_bytes=restart,ic_bytes=ic,per_case_bytes=per,pair_bytes=2*per,
        formula='104 snapshots + 3 measured restart sets + IC +256MiB logs, then20% overall margin. Separate10GiB reserve on guest and Windows backing volume.')

def validate_case(record):
    folder=Path(record['directory']);p=record['physics'];values=parameters((folder/'params.txt').read_text());ic,_=read(folder/'ics.hdf5')
    rows=[];largest=0;initial=None
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        a,row=native_summary(path,p);other,t=independent(path,p)
        if len(a['Masses'])!=65536 or not np.array_equal(a['ParticleIDs'],ic['ParticleIDs']):raise ValueError('Native count/IDs differ')
        if t!=row['time_code']:raise ValueError('Independent/native header times differ')
        errors={key:abs(value-row[key])/max(abs(row[key]),1e-12) for key,value in other.items()};largest=max(largest,max(errors.values()))
        if largest>1e-11:raise ValueError('Independent mass discrepancy')
        row['independent_relative_errors']=errors
        if initial is None:initial=initial_checks(a,ic,p)
        row['dense_mass_over_initial']=row['dense_mass']/(rows[0]['dense_mass'] if rows else row['dense_mass'])
        rows.append(row)
    times=cadence([r['time_code'] for r in rows],p,values)
    if sha(folder/'params.txt')!=record['input_sha256'] or sha(folder/'ics.hdf5')!=record['ic_sha256']:raise ValueError('Inputs changed during run')
    restart_files=list((folder/'output/restartfiles').glob('restart.*'))
    if len(restart_files)!=8:raise ValueError('Unexpected restart generations; preserve and review')
    record.update(status='complete_independent_checks',cadence=times,initial_checks=initial,series=rows,independent_max_relative_mass_error=largest,
        retained_restarts=[dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path)) for path in restart_files])
    return record

def run_case(folder,mode,p,retention):
    dependencies();require_storage(storage_snapshot(ROOT),retention['per_case_bytes'])
    if psutil.virtual_memory().available<12*GIB:raise RuntimeError('Insufficient native RAM reserve')
    values=full_inputs((ROOT/'params_L3.txt').read_text(),p);generate(folder,3,mode,p)
    param=folder/'params.txt';param.write_text(''.join(f'{key:34s} {value}\n' for key,value in values.items()))
    command=['mpirun','--bind-to','core','-np','8',str(ROOT/'Gadget4_pair'),'params.txt']
    record=dict(status='running',code='Gadget-4 SPH',level=3,mode=mode,directory=str(folder),physics=p,command=command,
        binary_sha256=EXPECTED_BINARY,input_sha256=sha(param),ic_sha256=sha(folder/'ics.hdf5'))
    save(folder/'result.json',record);print('START '+str(folder),flush=True)
    start=time.monotonic();peak=0;previous={};last_sample=start;last_guard=start;guard=None
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resource:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            now=time.monotonic();rss=0;cpu_delta=0;current={}
            try:
                for child in handle.children(recursive=True):
                    try:
                        rss+=child.memory_info().rss;cpu=child.cpu_times();total=cpu.user+cpu.system;current[child.pid]=total
                        if child.pid in previous:cpu_delta+=max(0,total-previous[child.pid])
                    except psutil.NoSuchProcess:pass
            except psutil.NoSuchProcess:pass
            peak=max(peak,rss);available=psutil.virtual_memory().available
            resource.write(json.dumps(dict(elapsed_seconds=now-start,rss_bytes=rss,available_bytes=available,busy_cpu_cores=cpu_delta/max(now-last_sample,1e-6)))+'\n');resource.flush()
            previous=current;last_sample=now
            if available<2*GIB or now-start>6000:guard='RAM/runtime guard'
            if now-last_guard>30:
                try:require_storage(storage_snapshot(ROOT),0)
                except Exception as exc:guard='Storage guard: '+str(exc)
                last_guard=time.monotonic()
            if guard:
                (folder/'output').mkdir(exist_ok=True);(folder/'output/stop').touch(exist_ok=False)
                try:proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:pass
    record.update(status='solver_finished_pending_validation',returncode=proc.returncode,wall_seconds=time.monotonic()-start,peak_child_rss_gib=peak/GIB,guard=guard)
    save(folder/'result.json',record)
    try:
        if guard or proc.returncode:raise RuntimeError('Native run did not finish normally')
        log=(folder/'run.log').read_text()
        if any(flag not in log for flag in CONFIG) or 'INIT: Hsml seed uses mean gas particle mass' not in log:raise ValueError('Native runtime build mismatch')
        record=validate_case(record);save(folder/'result.json',record)
    except Exception as exc:record.update(status='needs_review',error=str(exc));save(folder/'result.json',record);raise
    print(f"FINISH mode={mode}: {record['cadence']['native_snapshots']} native states, {record['wall_seconds']:.2f}s, peakRSS{record['peak_child_rss_gib']:.3f}GiB",flush=True)
    return record

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    dependencies();bundle=json.loads((Path(__file__).parent/'bundle.json').read_text())
    for name,digest in bundle['files'].items():
        if sha(Path(__file__).parent/name)!=digest:raise ValueError('Frozen full runner changed')
    if sha(ROOT/'verification_v2.json')!=bundle['verification_sha256']:raise ValueError('Native validation changed')
    proof=json.loads((ROOT/'verification_v2.json').read_text())
    if proof['status']!='passed_L3_initial_and_short_evolved_mass_checks':raise ValueError('Missing native validation')
    dest=ROOT/'full_l3_v1'
    if dest.exists():raise ValueError('Existing full batch cannot be restarted or overwritten')
    retention=budget();require_storage(storage_snapshot(ROOT),retention['pair_bytes']);p=metadata()
    dest.mkdir();batch=dict(status='running',budget=retention,finished=[]);save(dest/'batch.json',batch)
    try:
        for mode in (0,1):
            folder=dest/('tanh13' if mode else 'sharp13');folder.mkdir();batch['active_directory']=str(folder);save(dest/'batch.json',batch)
            case=run_case(folder,mode,p,retention);batch['finished'].append(case);save(dest/'batch.json',batch)
        a,b=batch['finished']
        if a['input_sha256']!=b['input_sha256']:raise ValueError('Pair inputs differ')
        paired_nonvelocity(read(Path(a['directory'])/'ics.hdf5')[0],read(Path(b['directory'])/'ics.hdf5')[0])
        paired_nonvelocity(read(a['series'][0]['snapshot'])[0],read(b['series'][0]['snapshot'])[0])
        batch['status']='complete_independent_checks';batch.pop('active_directory',None)
    except Exception as exc:batch.update(status='stopped_needs_review',error=str(exc));raise
    finally:save(dest/'batch.json',batch)

if __name__=='__main__':main()
