"""Isolated native RAMSES build; canonical source/objects/binaries remain unchanged."""
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot, require_storage, GIB
ROOT=Path('/home/kaan/sensitivity_20260907/ramses')
NATIVE=Path('/home/kaan/codes/ramses')
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/ramses/source')
BUILD=NATIVE/'bin_sensitivity_20260908'

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    ROOT.mkdir(exist_ok=False)
    require_storage(storage_snapshot(ROOT),GIB)
    historical=Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/codes/ramses/patch/cloudwind_l6/condinit.f90')
    if 'fv = 0.5d0*(1.0d0 - tanh((r-rv_scale*r_cloud)/edge))' not in historical.read_text():
        raise ValueError('Historical-law provenance missing')
    watched={}
    for sub in ('amr','hydro','pm','poisson','io','utils/scripts','patch/cloudwind_l6','bin_ic20260907_rect'):
        for p in (NATIVE/sub).rglob('*'):
            if p.is_file():watched[str(p)]=sha(p)
    BUILD.mkdir(exist_ok=False)
    patch=ROOT/'patch';patch.mkdir()
    for name in ('condinit.f90','read_params.f90'):shutil.copy2(STAGED/name,patch/name)
    if sha(patch/'read_params.f90')!=sha(NATIVE/'patch/cloudwind_l6/read_params.f90'):
        raise ValueError('Rectangular mesh patch changed')
    for name in ('Makefile','clusters.mk'):shutil.copy2(NATIVE/'bin_ic20260907_rect'/name,BUILD/name)
    shutil.copy2(historical,ROOT/'historical_condinit.f90')
    command=['nice','-n','19','make','-j1','NDIM=3','MPI=1','NPSCAL=1',
             'PATCH='+str(patch),'EXEC=ramses_pair']
    with (ROOT/'build.log').open('x') as log:
        subprocess.run(command,cwd=BUILD,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    if any(sha(p)!=h for p,h in watched.items()):raise ValueError('Canonical file changed during build')
    binary=ROOT/'ramses_pair3d';shutil.copy2(BUILD/'ramses_pair3d',binary)
    record=dict(binary=str(binary),binary_sha256=sha(binary),built_unix=time.time(),
        command=command,build_directory=str(BUILD),native_files_unchanged=watched,
        sources={str(p):sha(p) for p in patch.iterdir()},historical_source=str(historical),
        historical_sha256=sha(historical),native_precision='NPRE=8; all six primitive fields float64',
        scope='Unchanged native MUSCL/HLLC solver and rectangular mesh patch; runtime velocity_ic selects only velocity law.')
    (ROOT/'build.json').write_text(json.dumps(record,indent=2))
    print(json.dumps({k:record[k] for k in ('binary','binary_sha256','scope')}),flush=True)

if __name__=='__main__':main()
