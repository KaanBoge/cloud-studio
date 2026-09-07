"""Native RAMSES paired controls, retaining every output and actual timestamp.

Same native MUSCL/HLLC executable, rectangular mesh, tracer, precision and inputs
within each pair. Only velocity_ic changes. Full native outputs are also RAMSES
restart datasets, but checkpoint resume is not certified by this experiment.
"""
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
import numpy as np
import psutil
sys.path.insert(0,'/home/kaan/verified_20260907')
from run_params import parse_file,read_values
from ramses_native import read_output
from storage_guard import storage_snapshot,require_storage,GIB
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
ROOT=Path('/home/kaan/sensitivity_20260907/ramses')
TEMPLATE=Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/evidence/ramses_rect_tests/chi100/run.nml')

def save(path,data):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,allow_nan=False));tmp.replace(p)

def replace_scalar(text,key,value):
    pattern=rf'(?mi)^\s*{re.escape(key)}\s*=.*$'
    if len(re.findall(pattern,text))!=1:raise ValueError('Ambiguous/missing parameter '+key)
    return re.sub(pattern,f'{key} = {value}',text)

def input_for(level,mode,smoke=False):
    if level not in (3,4,5) or mode not in (0,1):raise ValueError('Unvalidated case')
    text=TEMPLATE.read_text();tcc=math.sqrt(100)/(2*math.sqrt(5/3))
    for key,value in dict(levelmin=level+2,levelmax=level+2,
        tend=.001 if smoke else 5*tcc,delta_tout=.001 if smoke else tcc/20,
        v_wind=2*math.sqrt(5/3),u_bound=2*math.sqrt(5/3),
        ngridmax=100000 if level<5 else 250000).items():
        text=replace_scalar(text,key,repr(value))
    return text.replace('&CLOUDWIND_PARAMS',f'&CLOUDWIND_PARAMS\nvelocity_ic = {mode}',1)

def no_mode(text):
    pattern=r'(?m)^velocity_ic = [01]$'
    if len(re.findall(pattern,text))!=1:raise ValueError('Ambiguous velocity mode')
    return re.sub(pattern,'',text)

def parameters(path):
    p=parse_file(path);_,v,_=read_values(path)
    for key in ('edge','x_cloud','y_cloud','z_cloud','levelmin','levelmax','velocity_ic','boxlen','nx','ny','nz','courant_factor'):
        p[key]=v[key]
    p['dimensions']=[2**int(p['levelmin'])*int(v[a]) for a in ('nx','ny','nz')]
    if p['levelmin']!=p['levelmax'] or p['dimensions'][0]!=2*p['dimensions'][1] or p['dimensions'][1]!=p['dimensions'][2]:
        raise ValueError('Not the matched uniform rectangular grid')
    if not math.isclose(p['mach'],2,rel_tol=1e-12) or p['chi']!=100 or p['velocity_ic'] not in (0,1):raise ValueError('Wrong physical case')
    return p

def ordered_grid(meta,c,params):
    dims=np.array(params['dimensions']);n=int(np.prod(dims));dx=params['boxlen']/dims[0]
    if meta['nvar']!=6 or c.shape!=(n,10) or meta['ncpu']!=8:raise ValueError('Wrong field/cell/shard count')
    if not np.all(np.isfinite(c)) or np.min(c[:,4])<=0 or np.min(c[:,8])<=0:raise ValueError('Nonfinite or nonpositive native fields')
    if not math.isclose(meta['gamma'],params['gamma'],rel_tol=1e-14) or not np.array_equal(meta['domain_width'],[20,10,10]):
        raise ValueError('Wrong domain or Gamma')
    if not np.allclose(c[:,3],dx,rtol=0,atol=1e-12):raise ValueError('Nonuniform cell widths')
    indices=np.rint(c[:,:3]/dx-.5).astype(np.int64)
    if np.any(indices<0) or np.any(indices>=dims) or not np.allclose(c[:,:3],(indices+.5)*dx,rtol=0,atol=1e-12):
        raise ValueError('Out-of-domain or off-grid native cells')
    flat=np.ravel_multi_index(indices.T,tuple(dims));order=np.argsort(flat)
    if not np.array_equal(flat[order],np.arange(n)):raise ValueError('Missing or overlapping grid cells')
    return c[order]

def raw(path,params):
    descriptor=(Path(path)/'hydro_file_descriptor.txt').read_text()
    rows=[line.split(',') for line in descriptor.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if [(a[1].strip(),a[2].strip()) for a in rows]!=[(n,'d') for n in ('density','velocity_x','velocity_y','velocity_z','pressure','scalar_00')]:
        raise ValueError('Unexpected native field descriptor/precision')
    meta,c=read_output(path);c=ordered_grid(meta,c,params)
    return dict(time=meta['time'],xyz=c[:,:3],dv=c[:,3]**3,rho=c[:,4],vel=c[:,5:8],pressure=c[:,8],
                tracer_concentration=c[:,9],metadata=meta)

def check_initial(d,p,mode):
    if d['time']!=0:raise ValueError('Missing t=0')
    rad=np.linalg.norm(d['xyz']-[p['x_cloud'],p['y_cloud'],p['z_cloud']],axis=1)
    f=.5*(1-np.tanh((rad-p['r_cloud'])/p['edge']));ref=p['rho_wind']*(1+(p['chi']-1)*f)
    vx=p['v_wind']*(1-.5*(1-np.tanh((rad-p['rv_scale']*p['r_cloud'])/p['edge']))) if mode else np.where(rad>p['rv_scale']*p['r_cloud'],p['v_wind'],0)
    errors=dict(density_relative=float(np.max(abs(d['rho']-ref)/ref)),
        velocity_over_wind=float(max(np.max(abs(d['vel'][:,0]-vx)),np.max(abs(d['vel'][:,1:])))/p['v_wind']),
        pressure_absolute=float(np.max(abs(d['pressure']-p['p_wind']))),
        tracer_concentration=float(np.max(abs(d['tracer_concentration']-f))))
    if max(errors.values())>1e-10:raise ValueError('Native IC mismatch '+str(errors))
    return errors

def pair_initial(a,b):
    if a['binary_sha256']!=b['binary_sha256']:raise ValueError('Different binaries')
    if no_mode((Path(a['directory'])/'run.nml').read_text())!=no_mode((Path(b['directory'])/'run.nml').read_text()):raise ValueError('Confounded inputs')
    da=raw(a['series'][0]['snapshot'],a['parameters']);db=raw(b['series'][0]['snapshot'],b['parameters'])
    for key in ('rho','tracer_concentration','xyz','dv'):
        if not np.array_equal(da[key],db[key]):raise ValueError('Initial pair mismatch '+key)
    pe=float(np.max(abs(da['pressure']-db['pressure'])));vd=float(np.max(abs(da['vel']-db['vel'])))
    if pe>1e-10 or vd<1e-8:raise ValueError('Pressure changed or velocity did not')
    return dict(initial_density_tracer_coordinates_volumes_exact=True,pressure_max_difference=pe,velocity_max_difference=vd)

def validate(folder,p,level,mode,smoke):
    rows=[]
    for path in sorted(folder.glob('output_?????')):
        if not path.is_dir():continue
        d=raw(path,p);mass=d['rho']*d['dv'];dense=d['rho']>p['rho_wind']*p['chi']/3
        row=dict(snapshot=str(path),time_code=d['time'],t_over_tcc=d['time']/p['t_cc'],cells=len(mass),
            dense_mass=float(mass[dense].sum()),tracer_mass=float(np.dot(mass,d['tracer_concentration'])),
            total_mass=float(mass.sum()),output_bytes=sum(f.stat().st_size for f in path.rglob('*') if f.is_file()))
        if d['time']==0:row['initial_checks']=check_initial(d,p,mode)
        rows.append(row);del d;gc.collect()
    rows.sort(key=lambda r:r['time_code'])
    if len(rows)<2 or rows[0]['time_code']!=0 or any(b['time_code']<=a['time_code'] for a,b in zip(rows,rows[1:])):
        raise ValueError('Missing initial/evolved output or nonmonotonic actual times')
    if not smoke:
        # Preserve native timestep-crossing times. No retiming to the nominal grid.
        dx=p['boxlen']/p['dimensions'][0]
        tol=1.02*p['courant_factor']*dx/(p['v_wind']+math.sqrt(p['gamma']*p['p_wind']/p['rho_wind']))/p['t_cc']
        actual=np.array([r['t_over_tcc'] for r in rows])
        if len(rows) not in (101,102) or not 5-1e-10<=actual[-1]<=5+tol:raise ValueError('Incomplete terminal cadence '+str(actual[-1]))
        if any(np.min(abs(actual-t))>tol for t in np.linspace(0,5,101)):raise ValueError('Missing scheduled snapshot')
    if rows[0]['dense_mass']<=0 or rows[0]['tracer_mass']<=0:raise ValueError('No initial mass')
    for row in rows:
        row['dense_mass_over_initial']=row['dense_mass']/rows[0]['dense_mass']
        row['tracer_mass_over_initial']=row['tracer_mass']/rows[0]['tracer_mass']
    return dict(unique_snapshots=len(rows),target_snapshots=101,series=rows,native_precision='All six native primitive fields float64, NPRE=8; all AMR/restart metadata retained')

def budget(level):
    # Use native eight-rank L3 smoke outputs, including mesh/boundary/ghost data.
    # Scaling from L3 overestimates per-cell boundary overhead on larger grids.
    proof=json.loads((ROOT/'smoke_batch.json').read_text())
    maximum=max(r['output_bytes'] for case in proof['finished'] for r in case['series'])
    return int(maximum*8**(level-3)*103*1.3+GIB/4)

def run_case(level,mode,smoke=False):
    b=json.loads((ROOT/'build.json').read_text());binary=b['binary']
    if sha(binary)!=b['binary_sha256']:raise ValueError('Pinned binary changed')
    folder=ROOT/('smokes' if smoke else 'runs')/f"L{level}_chi100_{'tanh13' if mode else 'sharp13'}"
    text=input_for(level,mode,smoke)
    if folder.exists():
        prior=json.loads((folder/'result.json').read_text())
        if prior.get('status')!='complete_native_checks' or (folder/'run.nml').read_text()!=text or prior['binary_sha256']!=b['binary_sha256']:
            raise ValueError('Existing partial case requires review; nothing overwritten')
        return prior
    disk=GIB if smoke else budget(level);storage=storage_snapshot(ROOT);require_storage(storage,disk)
    n=(8*2**level)*(4*2**level)**2
    if psutil.virtual_memory().available<max(n*1024,2*GIB)+2*GIB:raise RuntimeError('RAM guard')
    folder.mkdir(parents=True);(folder/'run.nml').write_text(text);p=parameters(folder/'run.nml')
    command=['mpirun','--bind-to','core','-np','8',binary,'run.nml']
    record=dict(status='running',level=level,mode=mode,directory=str(folder),parameters=p,command=command,
        binary_sha256=b['binary_sha256'],parameter_sha256=sha(folder/'run.nml'),storage_preflight=storage,
        reserved_output_gib=disk/GIB,started_unix=time.time(),
        launcher_sha256=sha(__file__),native_reader_sha256=sha('/home/kaan/verified_20260907/ramses_native.py'),
        template_sha256=sha(TEMPLATE))
    save(folder/'result.json',record);save(ROOT/'current.json',record);print('START '+str(folder),flush=True)
    peak=0;limited=False
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid)
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
    record.update(status='needs_review',returncode=proc.returncode,wall_seconds=time.time()-record['started_unix'],
                  peak_child_rss_gib=peak/GIB if peak else None,timeout=limited)
    save(folder/'result.json',record)
    if proc.returncode or limited:raise RuntimeError('Solver failed or reached cap; raw outputs retained')
    echo=(folder/'run.log').read_text()
    if f'[sensitivity] velocity_ic = {mode}' not in echo or 'Run completed' not in echo:raise ValueError('No native mode/completion echo')
    record.update(validate(folder,p,level,mode,smoke));record['status']='complete_native_checks'
    save(folder/'result.json',record);save(ROOT/'current.json',record)
    print(f'FINISH L{level} mode={mode}: {record["unique_snapshots"]} actual times; {record["wall_seconds"]:.1f}s',flush=True)
    return record

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    path=ROOT/('smoke_batch.json' if args.smoke else 'batch.json');batch=dict(status='running',finished=[],pairs=[],pid=os.getpid())
    try:
        if not args.smoke:
            proof=json.loads((ROOT/'smoke_batch.json').read_text())
            if proof['status']!='complete_native_checks' or len(proof['pairs'])!=1:raise ValueError('Validated native smoke pair required')
        for level in ((3,) if args.smoke else (3,4,5)):
            if no_mode(input_for(level,0,args.smoke))!=no_mode(input_for(level,1,args.smoke)):raise ValueError('Confounded pair')
            if not args.smoke:
                try:require_storage(storage_snapshot(ROOT),2*budget(level))
                except RuntimeError as error:
                    batch.update(status='held_storage',held_level=level,reason=str(error));print('HOLD '+str(error),flush=True);return
            pair=[]
            for mode in (0,1):
                pair.append(run_case(level,mode,args.smoke));batch['finished'].append(pair[-1]);save(path,batch)
            batch['pairs'].append(dict(level=level,checks=pair_initial(*pair)));save(path,batch)
        batch['status']='complete_native_checks'
    except Exception as error:
        batch.update(status='stopped_needs_review',error=str(error));raise
    finally:save(path,batch)

if __name__=='__main__':main()
