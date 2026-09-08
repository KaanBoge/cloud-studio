"""Isolated native Gadget-4 provenance and L3 smoke checks. No full queue here."""
import argparse,fcntl,hashlib,importlib.util,json,math,os,shutil,signal,subprocess,sys,time
from pathlib import Path
import h5py,numpy as np,psutil
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage,GIB

ROOT=Path('/home/kaan/sensitivity_20260907/gadget4')
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/gadget4')
NATIVE=Path('/home/kaan/codes/gadget4')
EXPECTED_BINARY='5ab857aba8cf4213fbce701ae8eaa6c449f5de43c0b9ab61722e962d88dca8d3'
CONFIG=['PERIODIC','NTYPES=2','LONG_Y_BITS=1','LONG_Z_BITS=1','DOUBLEPRECISION=2','POSITIONS_IN_32BIT','OUTPUT_PRESSURE']

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def save(path,value):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('x') as out:json.dump(value,out,indent=2,allow_nan=False)
    temp.replace(path)

def parameters(text):
    values={}
    for line in text.splitlines():
        line=line.split('%')[0].split('#')[0].strip()
        if not line:continue
        parts=line.split()
        if len(parts)!=2 or parts[0] in values:raise ValueError('Duplicate/malformed native parameter')
        values[parts[0]]=parts[1]
    return values

def metadata():
    p=json.loads((ROOT/'experiment.json').read_text())
    if (p['chi'],p['mach'],p['gamma'],p['r_cloud'],p['rv_scale'],p['ranks'])!=(100,2,5/3,1,1.3,8):raise ValueError('Unreviewed physical metadata')
    p['v_wind']=p['mach']*math.sqrt(p['gamma']*p['p_wind']/p['rho_wind'])
    p['t_cc']=math.sqrt(p['chi'])*p['r_cloud']/p['v_wind'];return p

def dependencies():
    build=json.loads((ROOT/'build.json').read_text())
    for name,digest in build['pinned_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Pinned file changed: '+name)
    return build

def read(path):
    with h5py.File(path) as h:
        a={k:v[:] for k,v in h['PartType0'].items()};head=h['Header'].attrs;t=float(head['Time'])
        count=len(a['ParticleIDs'])
        if int(head['NumPart_Total'][0])!=count or int(head['NumPart_ThisFile'][0])!=count or int(head['NumFilesPerSnapshot'])!=1:raise ValueError('Incomplete native file')
        if np.any(head['NumPart_Total'][1:]!=0) or float(head['BoxSize'])!=20:raise ValueError('Unexpected types/box')
    if not np.isfinite(t) or t<0 or len(np.unique(a['ParticleIDs']))!=count or np.any(a['ParticleIDs']==0):raise ValueError('Invalid native time/IDs')
    if any(len(v)!=count or not np.all(np.isfinite(v)) for v in a.values()):raise ValueError('Invalid native fields')
    order=np.argsort(a['ParticleIDs']);return {k:v[order] for k,v in a.items()},t

def law(radius,mode,p):
    if mode not in (0,1):raise ValueError('Unknown velocity law')
    return p['v_wind']*(1-.5*(1-np.tanh((radius-p['rv_scale']*p['r_cloud'])/(p['density_width']*p['r_cloud'])))) if mode else np.where(radius>p['rv_scale']*p['r_cloud'],p['v_wind'],0)

def check_ic(a,level,mode,p):
    if level not in (3,4):raise ValueError('Unreviewed level')
    dx=20/(8*2**level);dims=(8*2**level,4*2**level,4*2**level);pos=a['Coordinates'];cells=np.floor(pos/dx).astype(int)
    if len(pos)!=math.prod(dims) or np.max(abs(pos-(cells+.5)*dx))>1e-12 or len(np.unique(np.ravel_multi_index(cells.T,dims)))!=len(pos):raise ValueError('Unmatched IC lattice')
    r=np.linalg.norm(pos-p['center'],axis=1);rho=1+(p['chi']-1)*.5*(1-np.tanh((r-p['r_cloud'])/(p['density_width']*p['r_cloud'])))
    if np.max(abs(a['Masses']/dx**3-rho)/rho)>1e-13 or np.max(abs(a['InternalEnergy']*(p['gamma']-1)*rho-p['p_wind']))>1e-13:raise ValueError('IC density/pressure differs')
    if np.max(abs(a['Velocities'][:,0]-law(r,mode,p)))>1e-13 or np.any(a['Velocities'][:,1:]!=0):raise ValueError('Wrong IC velocity')
    if not np.array_equal(a['ParticleIDs']>=p['cloud_id_start'],r<=p['r_cloud']):raise ValueError('Cloud ID tagging differs')

def generate(folder,level,mode,p):
    if mode not in (0,1):raise ValueError('Unknown velocity mode')
    dest=folder/'ics.hdf5'
    if dest.exists():raise ValueError('Never overwrite native IC')
    writer=ROOT/('generator_historical.py' if mode else 'generator_sharp.py')
    spec=importlib.util.spec_from_file_location('pinned_g4_ic',writer);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if (module.MACH,module.GAMMA,module.DR,module.P0,module.NTYPES)!=(p['mach'],p['gamma'],p['density_width'],p['p_wind'],2):raise ValueError('Generator constants differ from metadata')
    module.make_ics(p['chi'],3,8*2**level,str(dest),p['rv_scale'])
    a,t=read(dest)
    if t!=0:raise ValueError('Nonzero IC time')
    check_ic(a,level,mode,p);return a

def prepare():
    if ROOT.exists():raise ValueError('Existing setup must not be overwritten')
    require_storage(storage_snapshot(NATIVE),GIB)
    test=subprocess.run([sys.executable,str(STAGED/'test_gadget_controls.py')],capture_output=True,text=True,check=True)
    sources={'Gadget4_pair':NATIVE/'Gadget4_3d_mixed_hfix','Config.sh':NATIVE/'Config_3d_mixed.sh',
        'generator_sharp.py':NATIVE/'ics/make_g4_cloudwind.py',
        'generator_historical.py':Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/codes/gadget4/ics/make_g4_cloudwind.py'),
        'experiment.json':STAGED/'experiment.json','gadget_controls.py':STAGED/'gadget_controls.py','test_gadget_controls.py':STAGED/'test_gadget_controls.py',
        'native_init.cc':NATIVE/'src/main/init.cc','native_init_original.cc':NATIVE/'src/main/init.cc.orig_prehsmlclamp',
        'native_run.cc':NATIVE/'src/main/run.cc','native_snap_io.cc':NATIVE/'src/io/snap_io.cc','native_snap_io.h':NATIVE/'src/io/snap_io.h',
        'native_constants.h':NATIVE/'src/data/constants.h','native_config.h':NATIVE/'build_hfix/gadgetconfig.h',
        'native_compiler.h':NATIVE/'build_hfix/compiler-command-line-args.h','native_version.cc':NATIVE/'build_hfix/version.cc',
        'historical_smoke.log':NATIVE/'runs/G4_3D_L3_chi100/smoke.log'}
    for level in (3,4):sources[f'params_L{level}.txt']=NATIVE/f'runs/G4_3D_L{level}_chi100/param.txt'
    if sha(sources['Gadget4_pair'])!=EXPECTED_BINARY:raise ValueError('Unexpected historical binary')
    for level in (3,4):
        if sha(NATIVE/f'runs/G4_3D_L{level}_chi100/Gadget4')!=EXPECTED_BINARY:raise ValueError('Historical ladder binary mismatch')
    if [x.strip() for x in sources['Config.sh'].read_text().splitlines() if x.strip() and not x.startswith('#')]!=CONFIG:raise ValueError('Native config changed')
    before={str(p):sha(p) for p in sources.values()};ROOT.mkdir()
    for name,path in sources.items():shutil.copy2(path,ROOT/name)
    if any(sha(p)!=digest for p,digest in before.items()):raise ValueError('Canonical source changed during copy')
    save(ROOT/'build.json',dict(status='pinned_not_evolved_validated',compiled_anything=False,original_hsml_patch_retained=True,
        native_git_commit=subprocess.check_output(['git','-C',str(NATIVE),'rev-parse','HEAD'],text=True).strip(),
        source_files_unchanged=before,pinned_files={name:sha(ROOT/name) for name in sources},expected_config=CONFIG,
        tests=dict(returncode=test.returncode,output=test.stdout+test.stderr)))

def smoke_inputs(template):
    v=parameters(template)
    if (v['MaxSizeTimestep'],v['CourantFac'],v['DesNumNgb'],v['MinEgySpec'],v['MaxMemSize'])!=('0.050000000','0.15','64','0','1000'):raise ValueError('Original native L3 settings differ')
    v.update(InitCondFile='./ics',OutputDir='./output',TimeMax='0.1',TimeBetSnapshot='0.1')
    return v

def native_summary(path,p):
    a,t=read(path)
    for key in ('Masses','Density','InternalEnergy','SmoothingLength','Pressure'):
        if key not in a or np.any(a[key]<=0):raise ValueError('Missing/nonpositive native '+key)
    pressure=(p['gamma']-1)*a['Density'].astype(float)*a['InternalEnergy'].astype(float)
    error=float(np.max(abs(pressure-a['Pressure'])/pressure))
    if error>8*np.finfo(a['Pressure'].dtype).eps:raise ValueError('Native stored/reconstructed pressure disagreement')
    mass=a['Masses'].astype(float)
    return a,dict(snapshot=str(path),sha256=sha(path),time_code=t,t_over_tcc=t/p['t_cc'],elements=len(mass),bytes=path.stat().st_size,
        fields={k:str(v.dtype) for k,v in a.items()},total_mass=float(mass.sum()),dense_mass=float(mass[a['Density']>p['chi']*p['rho_wind']/3].sum()),
        tagged_mass=float(mass[a['ParticleIDs']>=p['cloud_id_start']].sum()),pressure_reconstruction_max_relative=error)

def smoke(mode):
    dependencies();p=metadata();folder=ROOT/'smokes'/('L3_tanh13' if mode else 'L3_sharp13')
    if folder.exists():raise ValueError('Existing smoke must be retained, not relaunched')
    require_storage(storage_snapshot(ROOT),2*GIB)
    if psutil.virtual_memory().available<12*GIB:raise ValueError('Insufficient guarded RAM')
    v=smoke_inputs((ROOT/'params_L3.txt').read_text());folder.mkdir(parents=True);generate(folder,3,mode,p)
    param=folder/'params.txt';param.write_text(''.join(f'{k:34s} {value}\n' for k,value in v.items()))
    command=['mpirun','--bind-to','core','-np','8',str(ROOT/'Gadget4_pair'),'params.txt']
    record=dict(status='running',mode=mode,level=3,physics=p,command=command,directory=str(folder),binary_sha256=EXPECTED_BINARY,input_sha256=sha(param),ic_sha256=sha(folder/'ics.hdf5'))
    save(folder/'result.json',record);start=time.monotonic();peak=0
    with (folder/'run.log').open('x') as log:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid)
        try:
            while proc.poll() is None:
                try:peak=max(peak,sum(child.memory_info().rss for child in handle.children(recursive=True)))
                except psutil.NoSuchProcess:pass
                if time.monotonic()-start>600 or psutil.virtual_memory().available<2*GIB:raise RuntimeError('Native smoke runtime/RAM guard')
                try:proc.wait(timeout=.25)
                except subprocess.TimeoutExpired:pass
        except Exception as exc:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
            record.update(status='stopped_needs_review',error=str(exc));save(folder/'result.json',record);raise
    record.update(status='solver_finished_pending_validation',returncode=proc.returncode,wall_seconds=time.monotonic()-start,peak_child_rss_gib=peak/GIB)
    save(folder/'result.json',record)
    if proc.returncode:raise RuntimeError('Native smoke failed, preserve all outputs')
    log=(folder/'run.log').read_text()
    if any(flag not in log for flag in CONFIG) or 'INIT: Hsml seed uses mean gas particle mass' not in log:raise ValueError('Native runtime provenance mismatch')
    rows=[native_summary(path,p)[1] for path in sorted((folder/'output').glob('snapshot_*.hdf5'))]
    if len(rows)<2 or rows[0]['time_code']!=0 or abs(rows[-1]['time_code']-.1)>1e-8:raise ValueError('Native initial/evolved time missing')
    if sha(param)!=record['input_sha256'] or sha(folder/'ics.hdf5')!=record['ic_sha256']:raise ValueError('Native inputs changed')
    record.update(status='collected_pending_independent_validation',outputs=rows);save(folder/'result.json',record);return record

def main():
    args=argparse.ArgumentParser();args.add_argument('action',choices=['prepare','smoke']);action=args.parse_args().action
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    if action=='prepare':prepare();return
    dest=ROOT/'smoke_batch.json'
    if dest.exists():raise ValueError('Existing batch cannot be overwritten')
    batch=dict(status='running',finished=[])
    try:
        for mode in (0,1):batch['finished'].append(smoke(mode));save(dest,batch)
        batch['status']='collected_pending_independent_validation'
    except Exception as exc:batch.update(status='needs_review',error=str(exc));raise
    finally:save(dest,batch)

if __name__=='__main__':main()
