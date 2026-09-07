"""Native Enzo-E runtime-expression sensitivity pairs; no source rebuild.

Preserve PPM/density/boundaries and all seven native fields. This historical
Enzo-E recipe has NO passive tracer, so tracer retention cannot be certified.
Only initial velocity and its consistent kinetic energy differ within a pair.
"""
import argparse
import fcntl
import gc
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import h5py
import numpy as np
import psutil
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/enzo')
from run_enzo import save,sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage,GIB
ROOT=Path('/home/kaan/sensitivity_20260907/enzoe')
BASE=Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/evidence/enzoe_tests_v2/chi100/cloud.in')
HISTORICAL=Path('/home/kaan/codes/enzoe/runs/ENZOE2D_chi10_512/cloud_wind_chi10.in')
NATIVE=Path('/home/kaan/codes/enzoe/enzo-e/build/bin/enzo-e')
FIELDS=('density','velocity_x','velocity_y','velocity_z','total_energy','internal_energy','pressure')

def input_for(level,mode,smoke=False):
    if level not in (3,4,5) or mode not in (0,1):raise ValueError('Unvalidated case')
    nx=8*2**level;vw=2*math.sqrt(5/3);tcc=10/vw
    text=BASE.read_text().replace('# Audit test only. Density tanh, sharp velocity boundary at 1.3 R.','# Native Enzo-E sensitivity control, chi=100, Mach=2. No passive tracer in this recipe.')
    text=text.replace('root_size=[64,32,32]; root_blocks=[2,1,1];',f'root_size=[{nx},{nx//2},{nx//2}]; root_blocks=[4,2,1];')
    text=text.replace('Stopping { time=0.001; cycle=2; }',f'Stopping {{ time={.001 if smoke else 5*tcc:.17g}; cycle={2 if smoke else 500000}; }}')
    text=text.replace('step=0.001;',f'step={.001 if smoke else tcc/20:.17g};')
    if mode:
        density='(1.0 + 99.0 * 0.5 * (1.0 - tanh((sqrt(x*x+y*y+z*z) - 1.0) / 0.1)))'
        # Cello lexes '-0.5' as a signed number without separating whitespace.
        velocity=f'{vw:.17g}*(1.0 - 0.5*(1.0 - tanh((sqrt(x*x+y*y+z*z) - 1.3)/0.1)))'
        text=re.sub(r'(?m)^ velocity_x=.*$',f' velocity_x=[{velocity}];',text)
        text=re.sub(r'(?m)^ total_energy=.*$',f' total_energy=[1.5/{density}+0.5*({velocity})*({velocity})];',text)
    return text

def no_velocity(text):
    for key in ('velocity_x','total_energy'):
        if len(re.findall(rf'(?m)^ {key}=.*$',text))!=1:raise ValueError('Ambiguous initial expression')
        text=re.sub(rf'(?m)^ {key}=.*$','',text)
    return text

def params_for(text):
    dims=list(map(int,re.search(r'root_size=\[(\d+),(\d+),(\d+)\]',text).groups()))
    gamma=float(re.search(r'gamma=([^;]+);',text).group(1))
    stop=float(re.search(r'Stopping \{ time=([^;]+);',text).group(1))
    step=float(re.search(r'schedule \{ var="time"; step=([^;]+);',text).group(1))
    vw=float(re.search(r'value \{ density=1.0; velocity_x=([^;]+);',text).group(1))
    return dict(dimensions=dims,gamma=gamma,v_wind=vw,t_cc=10/vw,tmax=stop,output_dt=step,
        chi=100,r_cloud=1.,rho_wind=1.,p_wind=1.,mach=vw/math.sqrt(gamma),
        assumptions=['Chi, R, ambient density and pressure encoded directly in runtime expressions, not named native parameters; all are independently checked in native initial fields.',
        'No passive tracer in this native historical recipe.'])

def snapshot(paths,params,initial=False,mode=0,keep=False):
    dims=np.array(params['dimensions']);n=int(np.prod(dims));seen=np.zeros(n,dtype=bool)
    assembled={key:np.empty(n) for key in FIELDS};native_time=None;dtypes=set()
    for path in paths:
        with h5py.File(path) as h:
            t=float(h.attrs['time'][0])
            if native_time is None:native_time=t
            if t!=native_time:raise ValueError('Mixed processor output times')
            if h.attrs['rank'][0]!=3 or not np.allclose(h.attrs['lower'],[-3,-5,-5]) or not np.allclose(h.attrs['upper'],[17,5,5]):raise ValueError('Wrong native domain')
            for name,g in h.items():
                start=g.attrs['enzo_GridStartIndex'];end=g.attrs['enzo_GridEndIndex']+1
                widths=np.array(g.attrs['enzo_CellWidth']);lower=np.array(g.attrs['lower'])
                delta=np.array([20,10,10])/dims
                if not np.allclose(widths,delta,rtol=1e-12):raise ValueError('Wrong cell widths')
                lengths=end-start
                offsets=np.rint((lower-np.array([-3,-5,-5]))/delta).astype(int)
                coords=[np.arange(lengths[i])+offsets[i] for i in range(3)]
                z,y,x=np.meshgrid(coords[2],coords[1],coords[0],indexing='ij')
                if any(a.min()<0 or a.max()>=d for a,d in zip((x,y,z),dims)):raise ValueError('Cells outside domain')
                ids=(x+dims[0]*(y+dims[1]*z)).ravel()
                if seen[ids].any():raise ValueError('Overlapping/duplicated native cells')
                seen[ids]=True;region=tuple(slice(int(start[i]),int(end[i])) for i in (2,1,0))
                for key in FIELDS:
                    ds=g['field_'+key];dtypes.add(str(ds.dtype));assembled[key][ids]=ds[region].ravel()
    if not seen.all():raise ValueError('Missing native cells')
    if any(not np.all(np.isfinite(a)) for a in assembled.values()):raise ValueError('Nonfinite native field')
    rho=assembled['density'];vsq=sum(assembled['velocity_'+a]**2 for a in 'xyz')
    pressure=(params['gamma']-1)*rho*(assembled['total_energy']-.5*vsq)
    if rho.min()<=0 or pressure.min()<=0:raise ValueError('Nonpositive density/recovered pressure')
    dv=2000/n;dm=float(rho[rho>params['chi']/3].sum())*dv
    row=dict(files=[str(p) for p in paths],time_code=native_time,t_over_tcc=native_time/params['t_cc'],cells=n,
        dense_mass=dm,total_mass=float(rho.sum())*dv,native_dtypes=sorted(dtypes),tracer_mass=None,
        minimum_recovered_pressure=float(pressure.min()))
    if initial:
        if native_time!=0:raise ValueError('Missing t=0')
        z,y,x=np.indices((dims[2],dims[1],dims[0]));d=np.array([20,10,10])/dims
        rad=np.sqrt(((-3+(x+.5)*d[0])**2+(-5+(y+.5)*d[1])**2+(-5+(z+.5)*d[2])**2)).ravel()
        expected=1+99*.5*(1-np.tanh((rad-1)/.1));vw=params['v_wind']
        vx=vw*(1-.5*(1-np.tanh((rad-1.3)/.1))) if mode else np.where(rad>1.3,vw,0.)
        errors=dict(rho=float(np.max(abs(rho-expected)/expected)),velocity=float(np.max(abs(assembled['velocity_x']-vx)))/vw,
            transverse_velocity=float(max(np.max(abs(assembled['velocity_y'])),np.max(abs(assembled['velocity_z']))))/vw,
            pressure=float(np.max(abs(pressure-1))))
        if max(errors.values())>3e-5:raise ValueError('Initial field mismatch '+str(errors))
        row['initial_checks']=errors
    if keep:return row,assembled,pressure
    return row

def validate(folder,params,mode,smoke):
    grouped={}
    for p in sorted(folder.glob('ic-*-p*.h5')):
        count=int(re.fullmatch(r'ic-(\d+)-p\d+\.h5',p.name).group(1));grouped.setdefault(count,[]).append(p)
    rows=[snapshot(paths,params,i==0,mode) for i,paths in sorted(grouped.items())]
    if not rows or rows[0]['dense_mass']<=0:raise ValueError('No initial cloud output')
    times=np.array([r['t_over_tcc'] for r in rows])
    if not np.all(np.diff(times)>0):raise ValueError('Repeated/out-of-order native times')
    if smoke and (len(rows)!=2 or times[-1]<=0):raise ValueError('Smoke must contain initial and evolved outputs')
    if not smoke:
        if len(rows)!=101 or abs(times[-1]-5)>1e-5:raise ValueError('Incomplete native cadence '+str((len(rows),times[-1])))
        if np.max(abs(times-np.linspace(0,5,101)))>1e-5:raise ValueError('Off-cadence native times')
    for r in rows:r['dense_mass_over_initial']=r['dense_mass']/rows[0]['dense_mass']
    return dict(unique_snapshots=len(rows),series=rows,tracer_retention_available=False)

def pair_check(a,b):
    if a['binary_sha256']!=b['binary_sha256'] or no_velocity((Path(a['directory'])/'cloud.in').read_text())!=no_velocity((Path(b['directory'])/'cloud.in').read_text()):raise ValueError('Confounded pair')
    aa=snapshot([Path(p) for p in a['series'][0]['files']],a['parameters'],True,0,True)
    bb=snapshot([Path(p) for p in b['series'][0]['files']],b['parameters'],True,1,True)
    for key in ('density','internal_energy','velocity_y','velocity_z'):
        if not np.array_equal(aa[1][key],bb[1][key]):raise ValueError('Initial pair differs in '+key)
    if np.max(abs(aa[2]-bb[2]))>3e-5:raise ValueError('Pressure mismatch')
    if np.max(abs(aa[1]['velocity_x']-bb[1]['velocity_x']))<1e-8:raise ValueError('Velocity did not change')
    return dict(initial_density_internal_energy_transverse_velocities_exact=True,full_grid_coverage=True,
        tracer='Absent in both native inputs; retention cannot be certified.')

def budget(level):
    nx=8*2**level;padded=(nx//4+8)*(nx//4+8)*(nx//2+8)*8
    return int(padded*7*8*103*1.2+GIB)

def prepare():
    if (ROOT/'build.json').exists():return json.loads((ROOT/'build.json').read_text())
    ROOT.mkdir(exist_ok=False);require_storage(storage_snapshot(ROOT),GIB)
    history=HISTORICAL.read_text()
    if 'tanh((sqrt(x*x + y*y) - 1.3)/0.1)' not in history:raise ValueError('Historical law provenance mismatch')
    shutil.copy2(NATIVE,ROOT/'enzo-e');shutil.copy2(HISTORICAL,ROOT/'historical_2d_cloud.in');shutil.copy2(BASE,ROOT/'corrected_3d_audit.in')
    record=dict(binary=str(ROOT/'enzo-e'),binary_sha256=sha(ROOT/'enzo-e'),native_binary=str(NATIVE),native_binary_sha256=sha(NATIVE),
        historical_input=str(HISTORICAL),historical_sha256=sha(HISTORICAL),audited_3d_input=str(BASE),audited_input_sha256=sha(BASE),
        scope='Pinned unchanged native Enzo-E executable; runtime expressions only. Historical 2D radial velocity law extended spherically in the audited 3D setup. No passive tracer.')
    if record['binary_sha256']!=record['native_binary_sha256']:raise ValueError('Binary copy differs')
    save(ROOT/'build.json',record);return record

def run_case(level,mode,b,smoke):
    if sha(b['binary'])!=b['binary_sha256']:raise ValueError('Binary changed')
    text=input_for(level,mode,smoke);params=params_for(text)
    folder=ROOT/('smokes_v2' if smoke else 'runs')/f"L{level}_chi100_{'tanh13' if mode else 'sharp13'}"
    if folder.exists():
        old=json.loads((folder/'result.json').read_text())
        if old.get('status')!='complete_native_checks' or (folder/'cloud.in').read_text()!=text or old['binary_sha256']!=b['binary_sha256']:raise ValueError('Existing partial run requires review')
        return old
    disk=GIB if smoke else budget(level);storage=storage_snapshot(ROOT);require_storage(storage,disk)
    if psutil.virtual_memory().available<int(np.prod(params['dimensions']))*1024+2*GIB:raise RuntimeError('RAM guard')
    folder.mkdir(parents=True);(folder/'cloud.in').write_text(text)
    command=[b['binary'],'cloud.in','+p8'];rec=dict(status='running',level=level,mode=mode,directory=str(folder),parameters=params,
        command=command,binary_sha256=b['binary_sha256'],input_sha256=sha(folder/'cloud.in'),storage_preflight=storage,started_unix=time.time())
    save(folder/'result.json',rec);save(ROOT/'current.json',rec);print('START '+str(folder),flush=True)
    peak=0
    with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as res:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,handle.memory_info().rss+sum(p.memory_info().rss for p in handle.children(recursive=True)))
            except psutil.NoSuchProcess:pass
            res.write(json.dumps(dict(unix=time.time(),peak_solver_rss_bytes=peak,ram_available_bytes=psutil.virtual_memory().available))+'\n');res.flush()
            if time.time()-rec['started_unix']>(300 if smoke else 21600):
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:pass
    rec.update(status='needs_review',returncode=proc.returncode,wall_seconds=time.time()-rec['started_unix'],peak_solver_rss_gib=peak/GIB)
    save(folder/'result.json',rec)
    if proc.returncode:raise RuntimeError('Native Enzo-E failed; outputs retained')
    rec.update(validate(folder,params,mode,smoke));rec['status']='complete_native_checks'
    save(folder/'result.json',rec);save(ROOT/'current.json',rec);print(f'FINISH L{level} mode={mode}: {rec["unique_snapshots"]} native times, {rec["wall_seconds"]:.1f}s',flush=True);return rec

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');a=ap.parse_args();locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    b=prepare();batch=dict(status='running',finished=[],pairs=[],pid=os.getpid());out=ROOT/('smoke_batch_v2.json' if a.smoke else 'batch.json')
    try:
        if not a.smoke:
            if json.loads((ROOT/'smoke_batch_v2.json').read_text())['status']!='complete_native_checks':raise ValueError('Smoke pair required')
        for level in ((3,) if a.smoke else (3,4,5)):
            if no_velocity(input_for(level,0,a.smoke))!=no_velocity(input_for(level,1,a.smoke)):raise ValueError('Confounded inputs')
            if not a.smoke:
                try:require_storage(storage_snapshot(ROOT),2*budget(level))
                except RuntimeError as e:batch.update(status='held_storage',held_level=level,reason=str(e));print('HOLD '+str(e),flush=True);return
            pair=[]
            for mode in (0,1):pair.append(run_case(level,mode,b,a.smoke));batch['finished'].append(pair[-1]);save(out,batch)
            batch['pairs'].append(dict(level=level,checks=pair_check(*pair)));save(out,batch);gc.collect()
        batch['status']='complete_native_checks'
    except Exception as e:batch.update(status='stopped_needs_review',error=str(e));raise
    finally:save(out,batch)

if __name__=='__main__':main()
