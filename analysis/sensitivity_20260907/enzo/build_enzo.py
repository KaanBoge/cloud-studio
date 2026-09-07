"""Compile two isolated problem objects and relink Enzo's native solver objects.

Preserves all canonical sources, solver objects and binaries. Native build flags
are extracted from make's dry-run, not replaced with speculative optimizations.
"""
import fcntl
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage,GIB
ROOT=Path('/home/kaan/sensitivity_20260907/enzo')
SRC=Path('/home/kaan/codes/enzo/enzo-dev/src/enzo')
STAGED=Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/enzo/source')

def main():
    ROOT.mkdir(exist_ok=False)
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    require_storage(storage_snapshot(ROOT),2*GIB)
    names=('CloudWindInitialize.C','Grid_CloudWindInitializeGrid.C')
    watched=[SRC/n for n in names]+[SRC/'enzo.exe',SRC.parent.parent/'bin/enzo']
    before={str(p):sha(p) for p in watched}
    dry=subprocess.run(['make','-n','VERBOSE=1','-W',names[0],'-W',names[1]],cwd=SRC,capture_output=True,text=True,check=True)
    (ROOT/'native_make_dryrun.txt').write_text(dry.stdout)
    commands=[]
    for line in dry.stdout.splitlines():
        line=line.strip()
        if line.startswith('mpic++ '):
            line=line.split('>&',1)[0].split('>>',1)[0].rstrip(' \\;')
            args=shlex.split(line)
            if args not in commands:commands.append(args)
    replacements={};actual=[]
    for name in names:
        matches=[a for a in commands if '-c' in a and name in a]
        if len(matches)!=1:raise ValueError('Ambiguous compile command '+name+str(len(matches)))
        args=list(matches[0]);old=args[args.index('-o')+1];new=ROOT/(name+'.o')
        args[args.index('-o')+1]=str(new);args[args.index(name)]=str(STAGED/name)
        replacements[old]=str(new);actual.append(args)
    links=[a for a in commands if '-c' not in a and '-o' in a and any(x.endswith('.o') for x in a)]
    if len(links)!=1:raise ValueError('Ambiguous native link command '+str(len(links)))
    link=list(links[0]);link[link.index('-o')+1]=str(ROOT/'enzo_pair')
    inputs={}
    for i,x in enumerate(link):
        if x in replacements:link[i]=replacements[x]
        elif x.endswith(('.o','.a')):
            p=SRC/x;inputs[str(p)]=sha(p)
    headers={str(p):sha(p) for p in SRC.rglob('*.h')}
    for i,args in enumerate(actual+[link]):
        with (ROOT/f'build_{i}.log').open('x') as log:
            subprocess.run(['nice','-n','19']+args,cwd=SRC,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
    if any(sha(p)!=v for p,v in {**before,**inputs,**headers}.items()):raise ValueError('Native dependency changed during build')
    historical=Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/codes/enzo/enzo-dev/src/enzo/Grid_CloudWindInitializeGrid.C')
    if 'fv  = 0.5*(1.0 - tanh((sqrt(r2) - RvScale*CloudRadius)/SmoothWidth));' not in historical.read_text():
        raise ValueError('Historical-law provenance mismatch')
    record=dict(binary=str(ROOT/'enzo_pair'),binary_sha256=sha(ROOT/'enzo_pair'),built_unix=time.time(),
        commands=actual+[link],native_files_unchanged=before,linked_native_inputs=inputs,header_inputs=headers,
        sources={str(p):sha(p) for p in STAGED.glob('*.C')},historical_source=str(historical),historical_sha256=sha(historical),
        scope='Same native Enzo solver, flags and executable within each pair; only the runtime velocity mode changes. No canonical writes.')
    (ROOT/'build.json').write_text(json.dumps(record,indent=2))
    print(json.dumps({k:record[k] for k in ('binary','binary_sha256','scope')}),flush=True)

if __name__=='__main__':main()
