"""Native Arepo paired tests, explicit IC metadata, actual fields and full retention."""
import argparse,fcntl,json,math,os,re,signal,subprocess,sys,time
from pathlib import Path
import h5py,numpy as np,psutil
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage,GIB
ROOT=Path('/home/kaan/sensitivity_20260907/arepo')
FIELDS={'CenterOfMass','Coordinates','Density','InternalEnergy','Masses','ParticleIDs','PassiveScalars','Velocities'}

def save(path,d):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(d,indent=2,allow_nan=False));temp.replace(path)

def physics():
    build=json.loads((ROOT/'build.json').read_text());p=json.loads((ROOT/'experiment.json').read_text())
    if sha(ROOT/'experiment.json')!=build['pinned_files']['experiment.json']:raise ValueError('Physics metadata changed')
    if p['chi']!=100 or p['mach']!=2 or p['r_cloud']!=1 or p['gamma']!=5/3 or p['seed']!=42:raise ValueError('Unvalidated experiment')
    p['v_wind']=p['mach']*math.sqrt(p['gamma']*p['p_wind']/p['rho_wind']);p['t_cc']=math.sqrt(p['chi'])*p['r_cloud']/p['v_wind']
    return p

def native_params(text):
    vals={}
    for line in text.splitlines():
        line=line.split('%')[0].split('#')[0].strip()
        if not line:continue
        fields=line.split()
        if len(fields)!=2 or fields[0] in vals:raise ValueError('Ambiguous native parameter')
        vals[fields[0]]=fields[1]
    return vals

def input_for(level,smoke=False):
    if level not in (3,4,5):raise ValueError('Unvalidated level')
    p=physics();vals=native_params((ROOT/f'param_L{level}.txt').read_text())
    tmax=.1 if smoke else p['t_end_over_tcc']*p['t_cc']
    dt=.1 if smoke else p['output_dt_over_tcc']*p['t_cc']
    vals.update(TimeMax=repr(tmax),TimeBetSnapshot=repr(dt),TimeBetStatistics=repr(dt))
    for key,value in {'CoolingOn':0,'StarformationOn':0,'ComovingIntegrationOn':0,'PeriodicBoundariesOn':1,
        'OutputListOn':0,'TimeBegin':0,'TimeOfFirstSnapshot':0,'BoxSize':10,'NumFilesPerSnapshot':1,'ResubmitOn':0}.items():
        if float(vals[key])!=value:raise ValueError('Unreviewed native parameter '+key)
    return ''.join(f'{k:38s} {v}\n' for k,v in vals.items())

def ic_arrays(path):
    with h5py.File(path) as h:
        if float(h['Header'].attrs['Time'])!=0:raise ValueError('IC not at zero')
        return {k:v[:] for k,v in h['PartType0'].items()}

def check_ic(a,level,mode,p):
    n=(8*2**level)*(4*2**level)**2;dx=20/(8*2**level)
    if len(a['Masses'])!=n or not np.array_equal(a['ParticleIDs'],np.arange(1,n+1)):raise ValueError('IC IDs/count changed')
    if any(not np.all(np.isfinite(v)) for v in a.values()):raise ValueError('Nonfinite IC')
    dims=np.array([8*2**level,4*2**level,4*2**level]);indices=np.floor(a['Coordinates']/dx).astype(int)
    if np.any(indices<0) or np.any(indices>=dims) or not np.array_equal(np.ravel_multi_index(indices.T,tuple(dims)),np.arange(n)):
        raise ValueError('IC does not cover each original lattice cell exactly once')
    if np.max(abs(a['Coordinates']-(indices+.5)*dx))>.050000000001*dx:raise ValueError('Unmatched lattice jitter')
    r=np.linalg.norm(a['Coordinates']-p['center'],axis=1);f=.5*(1-np.tanh((r-p['r_cloud'])/p['density_width']))
    rho=p['rho_wind']+(p['chi']*p['rho_wind']-p['rho_wind'])*f
    vx=p['v_wind']*(1-.5*(1-np.tanh((r-p['rv_scale']*p['r_cloud'])/p['density_width']))) if mode else np.where(r>p['rv_scale']*p['r_cloud'],p['v_wind'],0)
    err=max(float(np.max(abs(a['Masses']/dx**3-rho)/rho)),float(np.max(abs(a['Velocities'][:,0]-vx))/p['v_wind']),
        float(np.max(abs(a['Velocities'][:,1:]))),float(np.max(abs((p['gamma']-1)*rho*a['InternalEnergy']-p['p_wind']))),
        float(np.max(abs(a['PassiveScalars'].reshape(-1)-f))))
    if err>1e-12:raise ValueError('IC does not match prescribed fields')
    return err

def raw(path,p):
    build=json.loads((ROOT/'build.json').read_text())
    with h5py.File(path) as h:
        if set(h['PartType0'])!=FIELDS:raise ValueError('Unexpected native fields')
        a={k:v[:] for k,v in h['PartType0'].items()};attrs=h['Header'].attrs
        if int(attrs['NumFilesPerSnapshot'])!=1 or int(attrs['NumPart_Total'][0])!=len(a['Masses']):raise ValueError('Incomplete native snapshot')
        flags={k+(f'={float(v)}' if np.issubdtype(type(v),np.number) else '') for k,v in h['Config'].attrs.items()}
        expected={x if '=' not in x else x.split('=')[0]+'='+str(float(x.split('=')[1])) for x in build['expected_config']}
        if flags!=expected:raise ValueError('Native compiled flags mismatch')
        for k,v in a.items():
            if k!='ParticleIDs' and v.dtype!=np.dtype('float64'):raise ValueError('Native precision changed')
            if not np.all(np.isfinite(v)):raise ValueError('Nonfinite native field '+k)
        ids=a['ParticleIDs'];order=np.argsort(ids)
        if len(np.unique(ids))!=len(ids) or np.any(ids==0):raise ValueError('Duplicate/invalid native IDs')
        a={k:v[order] for k,v in a.items()}
        if min(a['Density'].min(),a['Masses'].min(),a['InternalEnergy'].min())<=0:raise ValueError('Nonpositive native state')
        if np.any(a['Coordinates']<np.array(p['domain_left'])-1e-8) or np.any(a['Coordinates']>np.array(p['domain_right'])+1e-8):raise ValueError('Native positions outside domain')
        a['time']=float(attrs['Time']);a['pressure']=(p['gamma']-1)*a['Density']*a['InternalEnergy'];a['volume']=a['Masses']/a['Density']
        return a

def native_initial(d,ic,p,level):
    if d['time']!=0 or not np.array_equal(d['ParticleIDs'],ic['ParticleIDs']):raise ValueError('Native initial IDs/time mismatch')
    for key in ('Coordinates','Masses'):
        if not np.array_equal(d[key],ic[key]):raise ValueError('Native initial field changed '+key)
    for key in ('Velocities','InternalEnergy','PassiveScalars'):
        target=ic[key].reshape(d[key].shape);err=float(np.max(abs(d[key]-target)/np.maximum(abs(target),1)))
        if err>1e-12:raise ValueError('Native initial recovery mismatch '+key)
    rho_lattice=ic['Masses']/(20/(8*2**level))**3
    return dict(native_density_vs_lattice_max_relative=float(np.max(abs(d['Density']-rho_lattice)/rho_lattice)),
        native_pressure_vs_uniform_max_absolute=float(np.max(abs(d['pressure']-p['p_wind']))),
        native_volume_sum=float(d['volume'].sum()),scope='Native Voronoi values, not mass/lattice-volume; differences from analytic fields are reported, not erased.')

def pair_initial(a,b):
    if a['binary_sha256']!=b['binary_sha256'] or a['native_input_sha256']!=b['native_input_sha256']:raise ValueError('Confounded native pair')
    ia,ib=[ic_arrays(Path(c['directory'])/'IC.hdf5') for c in (a,b)]
    if set(ia)!=set(ib):raise ValueError('IC schemas differ')
    for key in ia:
        if key!='Velocities' and not np.array_equal(ia[key],ib[key]):raise ValueError('Other IC field changed '+key)
    da,db=[raw(Path(c['series'][0]['snapshot']),c['physics']) for c in (a,b)];errors={}
    for key in ('Coordinates','CenterOfMass','Masses','Density','ParticleIDs','volume'):
        if not np.array_equal(da[key],db[key]):raise ValueError('Native paired initial field differs '+key)
    for key in ('InternalEnergy','PassiveScalars','pressure'):
        errors[key]=float(np.max(abs(da[key]-db[key])/np.maximum(np.maximum(abs(da[key]),abs(db[key])),1e-300)))
        if errors[key]>1e-12:raise ValueError('Native paired thermodynamic/tracer change '+key)
    if np.max(abs(da['Velocities']-db['Velocities']))<1e-8:raise ValueError('Velocity mode did not change')
    return dict(ic_nonvelocity_fields_exact=True,native_initial_geometry_mass_density_exact=True,recovery_relative_errors=errors,
        velocity_difference=float(np.max(abs(da['Velocities']-db['Velocities']))))

def native_snapshots(folder):
    files=[]
    for path in folder.glob('snap_*.hdf5'):
        if re.fullmatch(r'snap_\d+\.hdf5',path.name):files.append(path)
        elif not re.fullmatch(r'snap_\d+\.hsml\.hdf5',path.name):raise ValueError('Unrecognized snapshot-like file '+path.name)
    return files

def validate(folder,p,level,mode,smoke):
    ic=ic_arrays(folder/'IC.hdf5');check_ic(ic,level,mode,p);rows=[]
    for path in native_snapshots(folder/'output'):
        d=raw(path,p);m=d['Masses'];rho=d['Density'];tr=d['PassiveScalars'];r=dict(snapshot=str(path),time_code=d['time'],t_over_tcc=d['time']/p['t_cc'],
            elements=len(m),dense_mass=float(m[rho>p['rho_wind']*p['chi']/3].sum()),total_mass=float(m.sum()),tracer_mass=float((m*tr).sum()),
            bytes=path.stat().st_size,volume_sum=float(d['volume'].sum()))
        if d['time']==0:r['native_initial_check']=native_initial(d,ic,p,level)
        rows.append(r)
    rows.sort(key=lambda r:r['time_code']);times=np.array([r['t_over_tcc'] for r in rows])
    if len(rows)<2 or times[0]!=0 or not np.all(np.diff(times)>0):raise ValueError('Incomplete/repeated native times')
    if not smoke:
        tol=float(native_params((folder/'param.txt').read_text())['MaxSizeTimestep'])/p['t_cc']+1e-8
        if len(rows) not in (101,102) or abs(times[-1]-5)>tol or any(min(abs(times-t))>tol for t in np.linspace(0,5,101)):raise ValueError('Incomplete full cadence')
    for row in rows:
        row['dense_mass_over_initial']=row['dense_mass']/rows[0]['dense_mass'];row['tracer_mass_over_initial']=row['tracer_mass']/rows[0]['tracer_mass']
    return dict(series=rows,unique_snapshots=len(rows),native_fields=sorted(FIELDS),initial_lattice_dimensions=[8*2**level,4*2**level,4*2**level])

def budget(level):
    proof=json.loads((ROOT/'smoke_batch_v2.json').read_text());sample=max(r['bytes'] for c in proof['finished'] for r in c['series'])
    return int(sample*8**(level-3)*103*1.4+GIB) # extra restart/IC/log allowance; no deletion credited

def run_case(level,mode,smoke=False):
    if mode not in (0,1):raise ValueError('Invalid mode')
    p=physics();build=json.loads((ROOT/'build.json').read_text());binary=build['binary']
    if sha(binary)!=build['binary_sha256']:raise ValueError('Pinned executable changed')
    folder=ROOT/('smokes_v2' if smoke else 'runs')/f"L{level}_chi100_{'tanh13' if mode else 'sharp13'}"
    text=input_for(level,smoke)
    if folder.exists():raise ValueError('Existing case requires review; never overwrite or blind-resume')
    required=GIB if smoke else budget(level);snap=storage_snapshot(ROOT);require_storage(snap,required)
    if psutil.virtual_memory().available<(p['ranks']*float(native_params(text)['MaxMemSize'])/1024+4)*GIB:raise RuntimeError('Insufficient available RAM')
    folder.mkdir(parents=True);(folder/'param.txt').write_text(text)
    generator=ROOT/('generator_historical.py' if mode else 'generator_sharp.py')
    if sha(generator)!=build['pinned_files'][generator.name]:raise ValueError('Pinned generator changed')
    gen=[sys.executable,str(generator),str(folder),str(p['chi']),str(4*2**level),'--ndim','3','--rv-scale',str(p['rv_scale']),'--seed',str(p['seed']),'--v-wind',repr(p['v_wind'])]
    with (folder/'generate.log').open('x') as log:subprocess.run(gen,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    check_ic(ic_arrays(folder/'IC.hdf5'),level,mode,p)
    command=['mpirun','--bind-to','core','-np',str(p['ranks']),binary,'param.txt']
    record=dict(status='running',level=level,mode=mode,directory=str(folder),physics=p,command=command,generate_command=gen,
        native_input_sha256=sha(folder/'param.txt'),ic_sha256=sha(folder/'IC.hdf5'),binary_sha256=sha(binary),launcher_sha256=sha(__file__),
        started_unix=time.time(),storage_preflight=snap,reserved_gib=required/GIB)
    save(folder/'result.json',record);save(ROOT/'current.json',record);print('START '+str(folder),flush=True)
    peak=0;limited=False
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as out:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'));handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(c.memory_info().rss for c in handle.children(recursive=True)))
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            out.write(json.dumps(dict(unix=time.time(),peak_child_rss_bytes=peak,ram_available=psutil.virtual_memory().available))+'\n');out.flush()
            if time.time()-record['started_unix']>(180 if smoke else 7200):
                limited=True;os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=.25 if smoke else 1)
            except subprocess.TimeoutExpired:pass
    record.update(status='needs_review',returncode=proc.returncode,timeout=limited,wall_seconds=time.time()-record['started_unix'],peak_child_rss_gib=peak/GIB if peak else None);save(folder/'result.json',record)
    if proc.returncode or limited:raise RuntimeError('Native solver failed/timed out; outputs retained')
    if sha(folder/'param.txt')!=record['native_input_sha256'] or sha(folder/'IC.hdf5')!=record['ic_sha256']:raise ValueError('Input changed during run')
    record.update(validate(folder,p,level,mode,smoke));record['status']='complete_native_checks';save(folder/'result.json',record);save(ROOT/'current.json',record)
    print(f'FINISH L{level} mode={mode}: {record["unique_snapshots"]} native times, {record["wall_seconds"]:.1f}s',flush=True);return record

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args();locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    path=ROOT/('smoke_batch_v2.json' if args.smoke else 'batch.json')
    if path.exists():raise ValueError('Existing batch requires review')
    batch=dict(status='running',finished=[],pairs=[],pid=os.getpid())
    try:
        if not args.smoke and json.loads((ROOT/'smoke_batch_v2.json').read_text())['status']!='complete_native_checks':raise ValueError('Native paired smokes required')
        if not args.smoke:
            proof=json.loads((ROOT/'setup_validation.json').read_text())
            if proof['status']!='passed' or proof['launcher_sha256']!=sha(__file__) or json.loads((ROOT/'yt_smoke_validation.json').read_text())['status']!='passed':
                raise ValueError('Current native and independent validation required')
        for level in ((3,) if args.smoke else (3,4)):
            if not args.smoke:
                try:require_storage(storage_snapshot(ROOT),2*budget(level))
                except RuntimeError as e:batch.update(status='held_storage',held_level=level,reason=str(e));return
            pair=[]
            for mode in (0,1):pair.append(run_case(level,mode,args.smoke));batch['finished'].append(pair[-1]);save(path,batch)
            batch['pairs'].append(dict(level=level,checks=pair_initial(*pair)));save(path,batch)
        batch['status']='complete_native_checks'
        if not args.smoke:
            try:require_storage(storage_snapshot(ROOT),2*budget(5))
            except RuntimeError as e:batch.update(status='held_storage',held_level=5,reason=str(e))
            else:batch.update(status='held_further_validation',held_level=5,reason='L5 requires separate runtime/restart-retention review; not launched automatically')
    except Exception as e:batch.update(status='stopped_needs_review',error=str(e));raise
    finally:save(path,batch)

if __name__=='__main__':main()
