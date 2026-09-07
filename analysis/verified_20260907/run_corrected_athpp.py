"""Opt-in, non-destructive 3D Athena++ runner for the corrected IC version.

Without --run, only writes a fresh input directory. Never deletes data, starts
other queues, uploads meshes or replaces old run IDs. Each invocation is one run.
It is not evidence that the twelve-code production comparison is complete.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from storage_guard import storage_snapshot, require_storage

ROOT=Path('/home/kaan/codes/athenapp/runs')
BIN=Path('/home/kaan/ic_audit_20260907/bin/athpp')
IC_VERSION='sharp13_20260907'


def make_input(level,chi,mach=2):
    nx=8*2**level; ny=nx//2
    mb=min(32,ny); tcc=math.sqrt(chi)/(mach*math.sqrt(5/3))
    return f'''# New non-radiative 3D run; density tanh, sharp velocity at 1.3 R.
# Custom pgen constants: R=1, rho_w=1, P_w=1. All time values are code time.
# Version: {IC_VERSION}; historical inputs/outputs are not changed.
<job>
problem_id = cloud_{IC_VERSION}_L{level}_chi{chi}
<time>
cfl_number = 0.4
nlim = -1
tlim = {5*tcc:.17g}
integrator = vl2
xorder = 2
ncycle_out = 100
<mesh>
nx1 = {nx}
nx2 = {ny}
nx3 = {ny}
x1min = -3
x1max = 17
x2min = -5
x2max = 5
x3min = -5
x3max = 5
ix1_bc = user
ox1_bc = outflow
ix2_bc = outflow
ox2_bc = outflow
ix3_bc = outflow
ox3_bc = outflow
refinement = none
<meshblock>
nx1 = {mb}
nx2 = {mb}
nx3 = {mb}
<hydro>
gamma = {5/3:.17g}
<problem>
Mach = {mach:.17g}
drat = {chi}
rv_scale = 1.3
<output1>
file_type = hst
dt = {tcc/20:.17g}
<output2>
file_type = hdf5
variable = prim
dt = {tcc/20:.17g}
<output3>
file_type = rst
dt = {tcc:.17g}
'''


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--level',type=int,choices=range(1,7),required=True)
    p.add_argument('--chi',type=int,choices=[10,100,1000],required=True)
    p.add_argument('--run',action='store_true')
    args=p.parse_args()
    proof=Path('/home/kaan/ic_audit_20260907/grid_tests')/f'athpp_chi{args.chi}'/'verification.json'
    verified=json.loads(proof.read_text())
    binary_sha=hashlib.sha256(BIN.read_bytes()).hexdigest()
    if not verified.get('passed') or verified['binary_sha256']!=binary_sha:
        raise ValueError('Pinned binary does not match the successful native IC test')
    nx=8*2**args.level; n=nx*(nx//2)**2
    needed_disk=n*120*101 + 5*1024**3  # conservative raw-output/restart allowance
    needed_ram=n*512 + 2*1024**3
    storage=storage_snapshot(ROOT)
    if args.run: require_storage(storage,needed_disk)
    available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
    if args.run and (shutil.disk_usage(ROOT).free<needed_disk or available<needed_ram):
        raise RuntimeError('Insufficient measured free space/memory for conservative retention budget; nothing was deleted')
    target=ROOT/f'IC_{IC_VERSION}_L{args.level}_chi{args.chi}'
    target.mkdir(exist_ok=False)
    param=target/'athinput'
    param.write_text(make_input(args.level,args.chi))
    blocks=n/min(32,nx//2)**3
    ranks=min(8,int(blocks))
    record={'ic_version':IC_VERSION,'status':'prepared','level':args.level,'chi':args.chi,
            'dimensions':[nx,nx//2,nx//2],'binary':str(BIN),'binary_sha256':binary_sha,
            'parameter_sha256':hashlib.sha256(param.read_bytes()).hexdigest(),
            'ranks':ranks,'target_snapshots':101,'production_validation':'pending',
            'storage_preflight':storage,
            'raw_retention':'all outputs retained; visualization is not an archive'}
    (target/'provenance.json').write_text(json.dumps(record,indent=2))
    print(f'Prepared {target}; run={args.run}',flush=True)
    if not args.run: return
    started=time.time()
    with (target/'run.log').open('x') as f:
        rc=subprocess.run(['nice','-n','5','mpirun','--bind-to','core','-np',str(ranks),str(BIN),'-i','athinput'],
                          cwd=target,stdout=f,stderr=subprocess.STDOUT).returncode
    import h5py
    times=[]
    for snap in target.glob('*.athdf'):
        with h5py.File(snap) as f: times.append(float(f.attrs['Time']))
    times=sorted(times); tcc=math.sqrt(args.chi)/(2*math.sqrt(5/3))
    import numpy as np
    matched=(len(times)==101 and np.allclose(np.array(times)/tcc,np.linspace(0,5,101),atol=1e-5,rtol=0))
    record.update(status='finished_cadence_verified' if rc==0 and matched else 'needs_review',
                  returncode=rc,wall_seconds=time.time()-started,snapshots=len(times),measured_times=times)
    (target/'provenance.json').write_text(json.dumps(record,indent=2))
    if record['status']=='needs_review': raise SystemExit(1)


if __name__=='__main__': main()
