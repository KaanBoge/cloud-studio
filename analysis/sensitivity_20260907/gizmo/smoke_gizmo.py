"""Native GIZMO smoke collection, with strict preflight and no production launch."""
import fcntl,importlib.util,json,math,os,signal,subprocess,sys,time
from pathlib import Path
import h5py,numpy as np,psutil
from setup_gizmo import ROOT,sha,storage_snapshot,require_storage,GIB

def save(path,record):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(record,indent=2,allow_nan=False));temp.replace(path)

def params(text):
    result={}
    for line in text.splitlines():
        line=line.split('%')[0].split('#')[0].strip()
        if not line:continue
        f=line.split()
        if len(f)!=2 or f[0] in result:raise ValueError('Malformed/duplicate native parameter')
        result[f[0]]=f[1]
    return result

def physics():
    build=json.loads((ROOT/'build.json').read_text());p=json.loads((ROOT/'experiment.json').read_text())
    if sha(ROOT/'experiment.json')!=build['pinned_files']['experiment.json']:raise ValueError('Metadata changed')
    if (p['chi'],p['mach'],p['gamma'],p['r_cloud'],p['mass_mode'],p['ranks'])!=(100,2,5/3,1,'volume',8):raise ValueError('Unvalidated physics')
    p['v_wind']=p['mach']*math.sqrt(p['gamma']*p['p_wind']/p['rho_wind']);p['t_cc']=math.sqrt(p['chi'])*p['r_cloud']/p['v_wind'];return p

def read(path):
    with h5py.File(path) as h:
        a={k:v[:] for k,v in h['PartType0'].items()};t=float(h['Header'].attrs['Time'])
        if int(h['Header'].attrs['NumPart_Total'][0])!=len(a['ParticleIDs']) or int(h['Header'].attrs['NumFilesPerSnapshot'])!=1:raise ValueError('Incomplete native file')
    ids=a['ParticleIDs'];order=np.argsort(ids)
    if len(np.unique(ids))!=len(ids) or np.any(ids==0):raise ValueError('Invalid IDs')
    if any(not np.all(np.isfinite(v)) for v in a.values()):raise ValueError('Nonfinite native state')
    return {k:v[order] for k,v in a.items()},t

def generate(folder,level,mode,p):
    writer=ROOT/('generator_historical.py' if mode else 'generator_sharp.py');build=json.loads((ROOT/'build.json').read_text())
    if sha(writer)!=build['pinned_files'][writer.name]:raise ValueError('Writer changed')
    spec=importlib.util.spec_from_file_location('pinned_ic',writer);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    dest=folder/'ics.hdf5'
    if dest.exists():raise ValueError('Never overwrite an IC')
    module.make_ic(chi=p['chi'],dx=20/(8*2**level),ndims=3,fname=str(dest),seed=p['seed'],mach=p['mach'],gamma=p['gamma'],rv_scale=p['rv_scale'],mass_mode=p['mass_mode'])
    a,t=read(dest);n=(8*2**level)*(4*2**level)**2
    if t!=0 or len(a['Masses'])!=n or not np.array_equal(a['ParticleIDs'],np.arange(1,n+1)):raise ValueError('IC count/time/IDs differ')
    pos=a['Coordinates'].astype(float);r=np.linalg.norm(pos-p['center'],axis=1);f=.5*(1-np.tanh((r-1)/.1));rho=1+(p['chi']-1)*f
    velocity=p['v_wind']*(1-.5*(1-np.tanh((r-p['rv_scale'])/.1))) if mode else np.where(r>p['rv_scale'],p['v_wind'],0)
    dx=20/(8*2**level)
    if np.max(abs(a['Masses']/dx**3-rho)/rho)>2e-7 or np.max(abs(a['InternalEnergy']*(p['gamma']-1)*rho-1))>2e-7:raise ValueError('IC density/energy mismatch')
    if np.max(abs(a['Velocities'][:,0]-velocity))/p['v_wind']>2e-7 or np.any(a['Velocities'][:,1:]!=0):raise ValueError('IC velocity mismatch')
    lattice=np.floor(pos/dx).astype(int);dims=(8*2**level,4*2**level,4*2**level)
    if np.max(abs(pos-(lattice+.5)*dx))>1e-6 or len(np.unique(np.ravel_multi_index(lattice.T,dims)))!=n:raise ValueError('Unmatched original lattice')
    return sha(dest)

def run_case(variant,mode):
    level=3;p=physics();build=json.loads((ROOT/'build.json').read_text());name=f'L3_{variant}_'+('tanh13' if mode else 'sharp13');folder=ROOT/'smokes'/name
    if folder.exists():raise ValueError('Existing smoke requires review')
    require_storage(storage_snapshot(ROOT),GIB)
    values=params((ROOT/f'params_{variant}_L3.txt').read_text());values.update(TimeMax='.1',TimeBetSnapshot='.1')
    if float(values['MaxSizeTimestep'])>=.1 or values['OutputDir']!='output' or values['InitCondFile']!='ics':raise ValueError('Unreviewed native input')
    if psutil.virtual_memory().available<(p['ranks']*float(values['MaxMemSize'])/1024+4)*GIB:raise ValueError('Available RAM below guarded native budget')
    binary=ROOT/f'GIZMO_{variant}_pair'
    if sha(binary)!=build['pinned_files'][binary.name]:raise ValueError('Native binary changed')
    folder.mkdir(parents=True);ic_hash=generate(folder,level,mode,p);param=folder/'params.txt';param.write_text(''.join(f'{k:32s} {v}\n' for k,v in values.items()))
    command=['mpirun','--bind-to','core','-np',str(p['ranks']),str(binary),'params.txt'];start=time.time();peak=0
    record=dict(variant=variant,mode=mode,level=3,directory=str(folder),physics=p,command=command,binary_sha256=sha(binary),input_sha256=sha(param),ic_sha256=ic_hash,status='running')
    save(folder/'result.json',record)
    with (folder/'run.log').open('x') as log:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'));handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(c.memory_info().rss for c in handle.children(recursive=True)))
            except psutil.NoSuchProcess:pass
            if time.time()-start>180:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                record.update(status='timeout',wall_seconds=time.time()-start);save(folder/'result.json',record);raise RuntimeError('Smoke timed out; raw preserved')
            try:proc.wait(timeout=.25)
            except subprocess.TimeoutExpired:pass
    record.update(returncode=proc.returncode,wall_seconds=time.time()-start,peak_child_rss_gib=peak/GIB)
    if proc.returncode:record['status']='failed';save(folder/'result.json',record);raise RuntimeError('Native smoke failed; preserve logs')
    log=(folder/'run.log').read_text();expected=build['expected_config'][variant]
    if any(flag not in log for flag in expected) or ('HYDRO_MESHLESS_FINITE_VOLUME' if variant=='mfm' else 'HYDRO_MESHLESS_FINITE_MASS') in log:raise ValueError('Native method flags differ')
    rows=[]
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        a,t=read(path)
        for field in ('Masses','Density','InternalEnergy','SmoothingLength'):
            if field not in a or np.any(a[field]<=0):raise ValueError('Missing/nonpositive native field '+field)
        rows.append(dict(snapshot=str(path),time=t,fields={k:str(v.dtype) for k,v in a.items()},elements=len(a['ParticleIDs']),bytes=path.stat().st_size))
    if len(rows)<2 or rows[0]['time']!=0 or rows[-1]['time']<.1-1e-8:raise ValueError('Missing native initial/evolved output')
    if sha(param)!=record['input_sha256'] or sha(folder/'ics.hdf5')!=ic_hash:raise ValueError('Input changed')
    record.update(status='native_outputs_collected_pending_pair_validation',outputs=rows);save(folder/'result.json',record);return record

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    dest=ROOT/'smoke_batch.json'
    if dest.exists():raise ValueError('Existing smoke batch requires review')
    batch=dict(status='running',finished=[])
    try:
        for v in ('mfm','mfv'):
            for m in (0,1):batch['finished'].append(run_case(v,m));save(dest,batch)
        batch['status']='collected_pending_pair_validation'
    except Exception as e:batch.update(status='needs_review',error=str(e));raise
    finally:save(dest,batch)

if __name__=='__main__':main()
