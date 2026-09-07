"""One opt-in corrected 3D run using measured level-5/6 performance profiles.

Default: prepare only. --run executes one run. --resume-prepared is only for
an untouched prepared directory, never a substitute for checkpoint restart.
No data deletion, hidden queues, output thinning, or legacy directory edits.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,'/home/kaan/verified_20260907')
from run_corrected_athpp import make_input
from run_params import parse_file
from storage_guard import storage_snapshot, require_storage

IC_VERSION='sharp13_20260907'
WORK=Path('/home/kaan/performance_20260907')
ROOTS={'athpp':Path('/home/kaan/codes/athenapp/runs'),'apk':Path('/home/kaan/codes/athenapk/runs')}
GIB=1024**3

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def set_sections(text,changes):
    parts=re.split(r'(?m)^\s*<([^>]+)>\s*$',text)
    present=set()
    for i in range(1,len(parts),2):
        name=parts[i].strip()
        if name not in changes:continue
        for key,val in changes[name].items():
            pattern=rf'(?m)^\s*{re.escape(key)}\s*=.*$'
            if re.search(pattern,parts[i+1]):parts[i+1]=re.sub(pattern,f'{key} = {val}',parts[i+1])
            else:parts[i+1]+=f'\n{key} = {val}\n'
        present.add(name)
    out=parts[0]+''.join(f'<{parts[i]}>\n{parts[i+1]}' for i in range(1,len(parts),2))
    for name in sorted(changes.keys()-present):
        out+=f'\n<{name}>\n'+''.join(f'{k} = {v}\n' for k,v in changes[name].items())
    return out

def input_for(code,level,chi,block,apk_compression=None):
    shape=[block]*3 if isinstance(block,int) else list(block)
    nx=8*2**level
    dims=[nx,nx//2,nx//2] if code=='athpp' else [nx//2,nx,nx//2]
    if len(shape)!=3 or any(not isinstance(b,int) or b<=0 or d%b for b,d in zip(shape,dims)):
        raise ValueError('Block shape must divide each native grid dimension exactly')
    if code=='athpp':
        return set_sections(make_input(level,chi),{'meshblock':{f'nx{i+1}':shape[i] for i in range(3)}})
    # Pinned, IC-verified native template. Remove obsolete historical comments.
    template=Path('/home/kaan/ic_audit_20260907/grid_tests/apk_chi100/athinput').read_text()
    template=template[template.index('<job>'):]
    template='\n'.join(line.split('#',1)[0].rstrip() for line in template.splitlines())
    nx=8*2**level;tcc=math.sqrt(chi)/(2*math.sqrt(5/3))
    text=set_sections(template,{'parthenon/mesh':{'nx1':nx//2,'nx2':nx,'nx3':nx//2},
        'parthenon/meshblock':{f'nx{i+1}':shape[i] for i in range(3)},
        'parthenon/time':{'tlim':repr(5*tcc),'nlim':-1},
        'problem/cloud':{'rho_cloud_cgs':chi,'v_wind_cgs':repr(2*math.sqrt(5/3)),'rv_scale':1.3},
        'parthenon/output0':{'dt':repr(tcc/20)},'parthenon/output1':{'dt':repr(tcc/20)},
        'parthenon/output2':{'file_type':'rst','dt':repr(tcc),'id':'restart'}})
    if apk_compression is not None:
        # Lossless prim-file encoding only; checkpoint compression is unchanged.
        if apk_compression!=1:raise ValueError('Only the separately tested compression profile is enabled')
        text=set_sections(text,{'parthenon/output1':{'hdf5_compression_level':1}})
    return '# Corrected custom 3D IC; density tanh, sharp velocity at 1.3 R.\n# Wind along +x2; native axes must be reordered for comparison. Sharp tracer differs from Athena++.\n'+text

def mpi_command(profile):
    if profile['ranks']==16:
        mpi=['mpirun','--use-hwthread-cpus','--bind-to','hwthread','--map-by','hwthread','-np','16']
    else:mpi=['mpirun','--bind-to','core','-np',str(profile['ranks'])]
    return mpi+[profile['binary'],'-i','athinput']

def check_proof(profile,chi):
    if sha(profile['binary'])!=profile['binary_sha256']:raise ValueError('Binary changed since benchmark')
    proof=json.loads((Path(profile['ic_proof_root'])/f"{profile['code']}_chi{chi}"/'verification.json').read_text())
    if not proof['passed'] or proof['binary_sha256']!=profile['binary_sha256']:
        raise ValueError('Binary lacks matching successful native IC proof')
    if not profile['regression']['passed']:raise ValueError('Field regression failed')
    if profile.get('hdf5_compression_level') is not None:
        io=profile.get('io_regression',{})
        if not io.get('passed') or not io.get('decoded_fields_exactly_equal') or io.get('candidate_binary_sha256')!=profile['binary_sha256']:
            raise ValueError('Lossless output profile lacks matching exact-field proof')

def budgets(profile):
    nx=8*2**profile['level'];n=nx*(nx//2)**2
    # Keep all 101 full precision native dumps AND restart files. Twenty percent
    # allowance on measured plot size, plus conservative 7*192 B/cell restarts.
    # Early uniform fields compress unusually well. Never extrapolate that
    # compression ratio to a late turbulent dataset: reserve uncompressed bytes.
    plot_bpc=max(48.1,profile['measured_native_output_bytes_per_cell'])
    disk=int(n*(plot_bpc*102*1.2+7*192)+10*GIB)
    ram=n*(512 if profile['code']=='athpp' else 160)+2*GIB
    return disk,ram

def validate_prepared(target,text,profile):
    record=json.loads((target/'provenance.json').read_text())
    if record['status']!='prepared':raise ValueError('Directory is not an untouched prepared run')
    if set(p.name for p in target.iterdir())!={'athinput','provenance.json'}:
        raise ValueError('Prepared directory contains additional files; refusing to overwrite')
    if (target/'athinput').read_text()!=text or sha(target/'athinput')!=record['parameter_sha256']:
        raise ValueError('Prepared input differs; review required')
    if record['binary_sha256']!=profile['binary_sha256'] or record['command']!=mpi_command(profile):
        raise ValueError('Prepared executable/settings differ; review required')
    return record

def inspect_cadence(target,code,tcc):
    import h5py
    import numpy as np
    rows=[]
    for path in target.glob('*.athdf' if code=='athpp' else '*.phdf'):
        with h5py.File(path) as f:
            t=float(f.attrs['Time'] if code=='athpp' else f['Info'].attrs['Time'])
        rows.append((t/tcc,path.name))
    rows.sort();unique=[];duplicates=[]
    for t,name in rows:
        if not math.isfinite(t):raise ValueError('Nonfinite native time')
        if unique and abs(t-unique[-1][0])<1e-10:duplicates.append((t,name))
        else:unique.append((t,name))
    ok=len(unique)==101 and bool(np.allclose([x[0] for x in unique],np.linspace(0,5,101),atol=1e-5,rtol=0))
    return dict(cadence_passed=ok,unique_snapshots=len(unique),native_time_rows=rows,
                duplicate_time_files_retained=duplicates,
                field_validation='pending; correct cadence alone is not scientific validation')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code',choices=['athpp','apk'],required=True)
    p.add_argument('--level',type=int,choices=[5,6],required=True)
    p.add_argument('--chi',type=int,choices=[10,100,1000],required=True)
    p.add_argument('--run',action='store_true')
    p.add_argument('--resume-prepared',action='store_true')
    a=p.parse_args()
    profile=json.loads((HERE/'optimized_profiles.json').read_text())[f'{a.code}_L{a.level}']
    check_proof(profile,a.chi)
    prefix=profile.get('directory_prefix','OPT')
    if prefix not in ('OPT','OPTIO1','OPTLTO'):raise ValueError('Unrecognized run-directory version')
    target=ROOTS[a.code]/f'{prefix}_{IC_VERSION}_L{a.level}_chi{a.chi}'
    text=input_for(a.code,a.level,a.chi,profile['block'],profile.get('hdf5_compression_level'))
    disk,ram=budgets(profile)
    # Lock spans both prepare and execute. CPU/GPU performance profiles were
    # measured separately: don't oversubscribe them by launching simultaneously.
    with (WORK/'production.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.resume_prepared:
            record=validate_prepared(target,text,profile)
            record.update(reserved_disk_gib=disk/GIB,reserved_ram_gib=ram/GIB)
            (target/'provenance.json').write_text(json.dumps(record,indent=2))
        else:
            target.mkdir(exist_ok=False)
            (target/'athinput').write_text(text)
            physical=parse_file(target/'athinput')
            assert math.isclose(physical['chi'],a.chi) and math.isclose(physical['mach'],2,rel_tol=1e-12)
            assert math.isclose(physical['tmax']/physical['t_cc'],5)
            assert math.isclose(physical['output_dt']/physical['t_cc'],.05)
            record=dict(status='prepared',profile=profile,ic_version=IC_VERSION,code=a.code,level=a.level,chi=a.chi,
               binary_sha256=profile['binary_sha256'],parameter_sha256=sha(target/'athinput'),
               physical_parameters=physical,command=mpi_command(profile),target_snapshots=101,
               dimensions_streamwise=[8*2**a.level,4*2**a.level,4*2**a.level],
               reserved_disk_gib=disk/GIB,reserved_ram_gib=ram/GIB,
               raw_retention='All native output/restarts retained. Meshes and MP4s are not raw archives.')
            (target/'provenance.json').write_text(json.dumps(record,indent=2))
        storage=storage_snapshot(target)
        record['storage_preflight']=storage
        (target/'provenance.json').write_text(json.dumps(record,indent=2))
        print(json.dumps({'directory':str(target),'run_requested':a.run,'profile':profile,
           'physical_parameters':record['physical_parameters'],'reserved_disk_gib':disk/GIB,
           'storage_preflight':storage},indent=2),flush=True)
        if not a.run:return
        require_storage(storage,disk)
        available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
        if shutil.disk_usage(target).free<disk or available<ram:
            raise RuntimeError('Insufficient free RAM or raw-retention disk budget; remains prepared, nothing deleted')
        if a.code=='apk':
            smi=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True)
            required=14000 if a.level==6 else 2600
            if int(smi.strip())<required:raise RuntimeError('Insufficient GPU headroom; remains prepared')
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        record.update(status='running',started_at_unix=time.time())
        (target/'provenance.json').write_text(json.dumps(record,indent=2))
        with (target/'run.log').open('x') as log:
            rc=subprocess.run(record['command'],cwd=target,stdout=log,stderr=subprocess.STDOUT,env=env).returncode
        try:result=inspect_cadence(target,a.code,record['physical_parameters']['t_cc'])
        except Exception as error:
            record.update(status='needs_review',returncode=rc,cadence_error=str(error),
                          wall_seconds=time.time()-record['started_at_unix'])
            (target/'provenance.json').write_text(json.dumps(record,indent=2))
            raise
        record.update(result,returncode=rc,wall_seconds=time.time()-record['started_at_unix'],
                      status='finished_cadence_verified' if rc==0 and result['cadence_passed'] else 'needs_review')
        (target/'provenance.json').write_text(json.dumps(record,indent=2))
        print(json.dumps(record,indent=2),flush=True)
        if record['status']=='needs_review':raise SystemExit(1)

if __name__=='__main__':main()
