"""Isolated native Athena 4.2 build, with no edits to production trees."""
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

ROOT=Path('/home/kaan/sensitivity_20260907/athw')
SRC=Path('/home/kaan/ic_audit_20260907/athw_build')
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/athw/cloud_wind.c')

def main():
    ROOT.mkdir(exist_ok=True)
    locks=[]
    for name in ('production.lock','benchmark.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    require_storage(storage_snapshot(ROOT),GIB)
    tree=ROOT/'build'
    tree.mkdir(exist_ok=False)
    shutil.copytree(SRC/'src',tree/'src',symlinks=True,ignore=shutil.ignore_patterns('*.o'))
    for name in ('Makefile','Makeoptions'):shutil.copy2(SRC/name,tree/name)
    shutil.copy2(STAGED,tree/'src/prob/shk_cloud.c')
    cmd=['nice','-n','19','make','-j2','all']
    with (ROOT/'build.log').open('x') as log:
        subprocess.run(cmd,cwd=tree,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    binfile=tree/'bin/athena'
    record=dict(binary=str(binfile),binary_sha256=sha(binfile),command=cmd,
        source=str(STAGED),source_sha256=sha(STAGED),built_unix=time.time(),
        historical_source='/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/CloudCrushing/A8/cloud_wind.c',
        scope='Both IC laws use the same native Athena 4.2 binary; no production source edits.')
    record['historical_source_sha256']=sha(record['historical_source'])
    (ROOT/'build.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
