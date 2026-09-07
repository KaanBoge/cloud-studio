"""Paired native FLASH 4.8 controls; retain full checkpoints and native plotfiles."""
import argparse
import fcntl
import gc
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import h5py
import numpy as np
import psutil
sys.path.insert(0,'/home/kaan/verified_20260907')
from run_params import parse_file,read_values
from storage_guard import storage_snapshot,require_storage,GIB
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
ROOT=Path('/home/kaan/sensitivity_20260907/flash')
TEMPLATE=Path('/home/kaan/ic_audit_20260907/grid_tests/flash_chi100/flash.par')
CHECK_FIELDS={'dens','dfcf','eint','ener','fllm','gamc','game','pres','shok','temp','velx','vely','velz'}
PLOT_FIELDS={'dens','pres','temp','velx','vely','velz'}

def save(path,obj):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,allow_nan=False));tmp.replace(p)

def input_for(level,mode,smoke=False):
    if level not in (3,4,5) or mode not in (0,1):raise ValueError('Unvalidated case')
    text='\n'.join(line.split('#',1)[0].strip() for line in TEMPLATE.read_text().splitlines())
    text='\n'.join(line for line in text.splitlines() if line)
    tcc=math.sqrt(100)*.1/(2*math.sqrt(5/3));dt=.001 if smoke else tcc/20
    changes=dict(lrefine_min=level-1,lrefine_max=level-1,nend=100 if smoke else 1000000,
        tmax=.001 if smoke else 5*tcc,plotfileIntervalTime=dt,checkpointFileIntervalTime=dt,
        rolling_checkpoint=10000,run_comment='"Velocity sensitivity: full native fields retained"')
    for key,value in changes.items():
        pat=rf'(?mi)^{re.escape(key)}\s*=.*$'
        if len(re.findall(pat,text))!=1:raise ValueError('Ambiguous parameter '+key)
        text=re.sub(pat,f'{key} = {value}',text)
    return text+f'\nsim_velocityIC = {mode}\n'

def no_mode(text):
    pat=r'(?m)^sim_velocityIC = [01]$'
    if len(re.findall(pat,text))!=1:raise ValueError('Ambiguous velocity mode')
    return re.sub(pat,'',text)

def parameters(path):
    p=parse_file(path);_,v,_=read_values(path)
    for key in ('sim_xctr','sim_yctr','sim_zctr','sim_smoothwidth','sim_velocityic','lrefine_min','lrefine_max','cfl'):
        p[key]=v[key]
    p['dimensions']=[32*2**(int(v['lrefine_min'])-1),16*2**(int(v['lrefine_min'])-1),16*2**(int(v['lrefine_min'])-1)]
    if v['lrefine_min']!=v['lrefine_max'] or p['chi']!=100 or not math.isclose(p['mach'],2,rel_tol=1e-12):raise ValueError('Wrong physical input/grid')
    return p

def named_values(dataset):
    return {row[0].decode().strip().lower():row[1].item() for row in dataset[:]}

def raw(path,p,full=False):
    checkpoint='_hdf5_chk_' in Path(path).name
    expected=CHECK_FIELDS if checkpoint else PLOT_FIELDS
    precision=np.dtype('float64' if checkpoint else 'float32')
    with h5py.File(path) as h:
        fields={key for key,v in h.items() if isinstance(v,h5py.Dataset) and v.ndim==4}
        if fields!=expected:raise ValueError('Unexpected native fields '+str(fields))
        leaves=h['node type'][:]==1;box=h['bounding box'][:][leaves];scalar=named_values(h['real scalars'])
        integers=named_values(h['integer runtime parameters'])
        if integers['sim_velocityic']!=int(p['sim_velocityic']):raise ValueError('Native IC mode echo mismatch')
        values={}
        for key in fields:
            a=h[key][:]
            if a.dtype!=precision or not np.all(np.isfinite(a)):raise ValueError('Nonfinite field or changed native precision '+key)
            if a.shape[1:]!=(16,16,16):raise ValueError('Unexpected native block size')
            values[key]=a[leaves].reshape(-1).astype(np.float64)
        if values['dens'].min()<=0 or values['pres'].min()<=0:raise ValueError('Nonpositive density/pressure')
        dims=np.array(p['dimensions']);n=int(np.prod(dims));dx=2./dims[0]
        if len(values['dens'])!=n:raise ValueError('Missing/unexpected active cells')
        delta=(box[:,:,1]-box[:,:,0])/16
        tol=1e-12 if checkpoint else 3e-7
        if not np.allclose(delta,dx,atol=tol,rtol=0):raise ValueError('Not the requested uniform mesh')
        centers=[box[:,a,0,None]+(np.arange(16)+.5)*delta[:,a,None] for a in range(3)]
        xyz=np.stack(np.broadcast_arrays(centers[0][:,None,None,:],centers[1][:,None,:,None],centers[2][:,:,None,None]),axis=-1).reshape(-1,3)
        idx=np.rint(xyz/dx-.5).astype(np.int64)
        if np.any(idx<0) or np.any(idx>=dims) or not np.allclose(xyz,(idx+.5)*dx,atol=tol,rtol=0):raise ValueError('Bad native coordinates')
        flat=np.ravel_multi_index(idx.T,tuple(dims));order=np.argsort(flat)
        if not np.array_equal(flat[order],np.arange(n)):raise ValueError('Overlapping/missing native cells')
        for key in values:values[key]=values[key][order]
        return dict(time=float(scalar['time']),rho=values['dens'],pressure=values['pres'],
            vel=np.stack([values['vel'+a] for a in 'xyz'],axis=1),dv=np.full(n,dx**3),xyz=xyz[order],
            fields=values if full else None,checkpoint=checkpoint)

def check_initial(d,p,mode):
    if d['time']!=0:raise ValueError('Missing native t=0')
    r=np.linalg.norm(d['xyz']-[p['sim_xctr'],p['sim_yctr'],p['sim_zctr']],axis=1)
    width=p['sim_smoothwidth']*p['r_cloud'];f=.5*(1-np.tanh((r-p['r_cloud'])/width))
    rho=p['rho_wind']+(p['rho_wind']*p['chi']-p['rho_wind'])*f
    vx=p['v_wind']*(1-.5*(1-np.tanh((r-p['rv_scale']*p['r_cloud'])/width))) if mode else np.where(r>p['rv_scale']*p['r_cloud'],p['v_wind'],0)
    errors=dict(density_relative=float(np.max(abs(d['rho']-rho)/rho)),
        velocity_over_wind=float(max(np.max(abs(d['vel'][:,0]-vx)),np.max(abs(d['vel'][:,1:])))/p['v_wind']),
        pressure_absolute=float(np.max(abs(d['pressure']-p['p_wind']))))
    if max(errors.values())>1e-10:raise ValueError('Native IC mismatch '+str(errors))
    return errors

def pair_field_checks(a,b):
    recovered={'temp','pres','eint','game'};errors={}
    for key in CHECK_FIELDS-{'velx','ener'}:
        if key in recovered:
            errors[key]=float(np.max(abs(a[key]-b[key])/np.maximum(np.maximum(abs(a[key]),abs(b[key])),1e-300)))
            if errors[key]>1e-13:raise ValueError('Thermodynamic change beyond recovery roundoff '+key)
        elif not np.array_equal(a[key],b[key]):raise ValueError('Other native initial field changed '+key)
    energy_error=float(np.max(abs((a['ener']-b['ener'])-.5*(a['velx']**2-b['velx']**2))))
    if energy_error>1e-13:raise ValueError('Inconsistent kinetic energy difference')
    return dict(recovered_fields_max_relative_differences=errors,consistent_energy_difference_max_error=energy_error)

def pair_initial(a,b):
    if a['binary_sha256']!=b['binary_sha256'] or no_mode((Path(a['directory'])/'flash.par').read_text())!=no_mode((Path(b['directory'])/'flash.par').read_text()):
        raise ValueError('Confounded pair')
    da=raw(a['series'][0]['snapshot'],a['parameters'],True);db=raw(b['series'][0]['snapshot'],b['parameters'],True)
    for key in ('rho','xyz','dv'):
        if not np.array_equal(da[key],db[key]):raise ValueError('Initial mismatch '+key)
    field_checks=pair_field_checks(da['fields'],db['fields'])
    vd=float(np.max(abs(da['vel']-db['vel'])))
    if vd<1e-8:raise ValueError('Velocity did not change')
    return dict(initial_density_coordinates_volumes_exact=True,unchanged_auxiliary_fields_exact=True,
                velocity_max_difference=vd,tracer_retention_available=False,**field_checks)

def validate(folder,p,mode,smoke):
    rows=[];plots=[]
    for path in sorted(folder.glob('*hdf5*')):
        d=raw(path,p);mass=d['rho']*d['dv'];dense=d['rho']>p['rho_wind']*p['chi']/3
        row=dict(snapshot=str(path),time_code=d['time'],t_over_tcc=d['time']/p['t_cc'],cells=len(mass),
            dense_mass=float(mass[dense].sum()),total_mass=float(mass.sum()),tracer_mass=None,bytes=path.stat().st_size)
        if d['checkpoint']:
            if d['time']==0:row['initial_checks']=check_initial(d,p,mode)
            rows.append(row)
        else:plots.append(row)
        del d;gc.collect()
    rows.sort(key=lambda r:r['time_code']);unique=[];duplicates=[]
    for row in rows:
        if unique and row['time_code']==unique[-1]['time_code']:duplicates.append(row)
        else:unique.append(row)
    if len(unique)<2 or unique[0]['time_code']!=0:raise ValueError('Missing initial/evolved checkpoint')
    if not smoke:
        tol=1.02*p['cfl']*(2/p['dimensions'][0])/(p['v_wind']+math.sqrt(p['gamma']*p['p_wind']/p['rho_wind']))/p['t_cc']
        times=np.array([r['t_over_tcc'] for r in unique])
        if len(unique) not in (101,102) or not 5-1e-10<=times[-1]<=5+tol:raise ValueError('Incomplete full-state cadence '+str((len(unique),times[-1])))
        if any(np.min(abs(times-t))>tol for t in np.linspace(0,5,101)):raise ValueError('Missing nominal-time checkpoint')
        plot_times=np.unique([r['time_code'] for r in plots])
        if not np.array_equal(plot_times,np.array([r['time_code'] for r in unique])):raise ValueError('Plot/checkpoint time coverage differs')
    for row in unique:row['dense_mass_over_initial']=row['dense_mass']/unique[0]['dense_mass']
    return dict(unique_snapshots=len(unique),target_snapshots=101,series=unique,plot_outputs=plots,
                exact_duplicate_checkpoints_retained=duplicates,tracer_retention_available=False,
                native_precision='13 full-state float64 checkpoint fields plus all original six-field float32 plotfiles')

def budget(level):
    proof=json.loads((ROOT/'smoke_batch.json').read_text())
    check=max(row['bytes'] for c in proof['finished'] for row in c['series'])
    plot=max(row['bytes'] for c in proof['finished'] for row in c['plot_outputs'])
    return int((check+plot)*8**(level-3)*103*1.3+GIB/4)

def run_case(level,mode,smoke=False):
    build=json.loads((ROOT/'build.json').read_text());binary=build['binary']
    if sha(binary)!=build['binary_sha256']:raise ValueError('Pinned binary changed')
    folder=ROOT/('smokes' if smoke else 'runs')/f"L{level}_chi100_{'tanh13' if mode else 'sharp13'}";text=input_for(level,mode,smoke)
    if folder.exists():
        old=json.loads((folder/'result.json').read_text())
        if old.get('status')!='complete_native_checks' or (folder/'flash.par').read_text()!=text or old['binary_sha256']!=build['binary_sha256']:raise ValueError('Existing partial case requires review')
        return old
    storage=storage_snapshot(ROOT);required=GIB if smoke else budget(level);require_storage(storage,required)
    # Existing MAXBLOCKS=1200 native arrays measured 13.42 GiB across eight
    # smoke ranks. Keep conservative headroom; do not infer RAM from cell count.
    if psutil.virtual_memory().available<19*GIB:raise RuntimeError('RAM guard: require 19 GiB available')
    folder.mkdir(parents=True);(folder/'flash.par').write_text(text);p=parameters(folder/'flash.par')
    command=['mpirun','--bind-to','core','-np','8',binary]
    record=dict(status='running',level=level,mode=mode,directory=str(folder),parameters=p,command=command,
        binary_sha256=build['binary_sha256'],input_sha256=sha(folder/'flash.par'),launcher_sha256=sha(__file__),
        started_unix=time.time(),storage_preflight=storage,reserved_output_gib=required/GIB)
    save(folder/'result.json',record);save(ROOT/'current.json',record);print('START '+str(folder),flush=True)
    peak=0;limited=False
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'));handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(q.memory_info().rss for q in handle.children(recursive=True)))
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            resources.write(json.dumps(dict(unix=time.time(),peak_child_rss_bytes=peak,ram_available_bytes=psutil.virtual_memory().available,loadavg=os.getloadavg()))+'\n');resources.flush()
            if time.time()-record['started_unix']>(300 if smoke else 21600):
                limited=True;os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=.25 if smoke else 1)
            except subprocess.TimeoutExpired:pass
    record.update(status='needs_review',returncode=proc.returncode,timeout=limited,wall_seconds=time.time()-record['started_unix'],peak_child_rss_gib=peak/GIB if peak else None)
    save(folder/'result.json',record)
    if proc.returncode or limited:raise RuntimeError('Solver failed or timed out; all raw retained')
    if f'[sensitivity] sim_velocityIC = {mode}' not in (folder/'run.log').read_text():raise ValueError('Native mode echo missing')
    record.update(validate(folder,p,mode,smoke));record['status']='complete_native_checks'
    save(folder/'result.json',record);save(ROOT/'current.json',record)
    print(f'FINISH L{level} mode={mode}: {record["unique_snapshots"]} distinct full-state times, {record["wall_seconds"]:.1f}s',flush=True)
    return record

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    batch=dict(status='running',finished=[],pairs=[],pid=os.getpid());path=ROOT/('smoke_batch.json' if args.smoke else 'batch.json')
    try:
        if not args.smoke and json.loads((ROOT/'smoke_batch.json').read_text())['status']!='complete_native_checks':raise ValueError('Native smoke pair required')
        for level in ((3,) if args.smoke else (3,4,5)):
            if no_mode(input_for(level,0,args.smoke))!=no_mode(input_for(level,1,args.smoke)):raise ValueError('Confounded pair')
            if not args.smoke:
                try:require_storage(storage_snapshot(ROOT),2*budget(level))
                except RuntimeError as error:batch.update(status='held_storage',held_level=level,reason=str(error));print('HOLD '+str(error),flush=True);return
            pair=[]
            for mode in (0,1):
                pair.append(run_case(level,mode,args.smoke));batch['finished'].append(pair[-1]);save(path,batch)
            batch['pairs'].append(dict(level=level,checks=pair_initial(*pair)));save(path,batch)
        batch['status']='complete_native_checks'
    except Exception as error:batch.update(status='stopped_needs_review',error=str(error));raise
    finally:save(path,batch)

if __name__=='__main__':main()
