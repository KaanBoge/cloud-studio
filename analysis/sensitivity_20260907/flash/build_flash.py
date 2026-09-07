"""Separate FLASH problem unit and object directory, without canonical overwrites."""
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
from storage_guard import storage_snapshot,require_storage,GIB
ROOT=Path('/home/kaan/sensitivity_20260907/flash')
NATIVE=Path('/home/kaan/CloudCrushing/FLASH4.8')
PROBLEM=NATIVE/'source/Simulation/SimulationMain/CloudCrush'
UNIT=NATIVE/'source/Simulation/SimulationMain/CloudCrushSensitivity_20260908'
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/flash/source')
BUILD=NATIVE/'object_sensitivity_20260908'

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    ROOT.mkdir(exist_ok=False);require_storage(storage_snapshot(ROOT),2*GIB)
    if BUILD.exists() or UNIT.exists():raise ValueError('Isolated unit/build already exists')
    historical=Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/CloudCrushing/FLASH4.8/source/Simulation/SimulationMain/CloudCrush/Simulation_initBlock.F90')
    if 'velFrac   = 0.5 * (1.0 - tanh((radius - sim_rvScale*sim_rCloud)/delta))' not in historical.read_text():
        raise ValueError('Historical-law provenance missing')
    before={str(p):sha(p) for parent in (PROBLEM,NATIVE/'object_ic20260907') for p in parent.iterdir() if p.is_file()}
    UNIT.mkdir()
    for name in ('Config','Simulation_data.F90','Simulation_init.F90','Simulation_initBlock.F90'):
        shutil.copy2(STAGED/name,UNIT/name)
    for name in ('Makefile','Grid_applyBCEdge.F90'):shutil.copy2(PROBLEM/name,UNIT/name)
    commands=[['./bin/setup.py',UNIT.name,'-auto','-3d','-nxb=16','-nyb=16','-nzb=16','-maxblocks=1200','-objdir='+BUILD.name],
              ['nice','-n','19','make','-C',str(BUILD),'-j2']]
    for i,command in enumerate(commands):
        with (ROOT/f'build_{i}.log').open('x') as log:
            subprocess.run(command,cwd=NATIVE,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('Canonical source/build changed')
    binary=ROOT/'flash4_pair';shutil.copy2(BUILD/'flash4',binary)
    params=(BUILD/'setup_params').read_text()
    if 'sim_velocityIC' not in params:raise ValueError('Native parameter not registered')
    record=dict(binary=str(binary),binary_sha256=sha(binary),built_unix=time.time(),commands=commands,
        native_files_unchanged=before,sources={str(p):sha(p) for p in UNIT.iterdir() if p.is_file()},
        historical_source=str(historical),historical_sha256=sha(historical),build_directory=str(BUILD),
        scope='Separate native FLASH 4.8 problem unit and object directory; same runtime-switchable executable within pairs.')
    (ROOT/'build.json').write_text(json.dumps(record,indent=2))
    print(json.dumps({k:record[k] for k in ('binary','binary_sha256','scope')}),flush=True)

if __name__=='__main__':main()
