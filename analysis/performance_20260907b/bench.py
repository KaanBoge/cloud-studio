"""Second-round isolated performance tests. Native fields, no production writes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import psutil
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/performance_20260907')
from run_optimized import input_for,set_sections,mpi_command

ROOT=Path('/home/kaan/performance_20260907b')
OLD='/home/kaan/performance_20260907/bin/athpp_native'
LTO=str(ROOT/'bin/athpp_lto')
APK='/home/kaan/ic_audit_20260907/bin/apk'

def run(name,code='athpp',level=5,block=(64,64,64),binary=OLD,compression=None,end=.6,ranks=16):
    folder=ROOT/'runs'/name
    if (folder/'result.json').exists():
        r=json.loads((folder/'result.json').read_text())
        if r['rc']:raise RuntimeError('Cached failure: '+name)
        expected=dict(code=code,level=level,block=list(block),ranks=ranks,compression=compression,
                      target_code_time=end,binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest())
        if any(r.get(k)!=v for k,v in expected.items()):
            raise RuntimeError('Cached inputs or binary changed; use a new test name: '+name)
        return r
    folder.mkdir(parents=True,exist_ok=False)
    text=input_for(code,level,100,block[0])
    output='output2' if code=='athpp' else 'parthenon/output1'
    if code=='athpp':
        text=text.split('<output3>')[0]
        changes={'time':{'tlim':end},'meshblock':{f'nx{i+1}':block[i] for i in range(3)},
                 'output1':{'dt':end},output:{'dt':end}}
    else:
        text=text.split('<parthenon/output2>')[0]
        changes={'parthenon/time':{'tlim':end},'parthenon/meshblock':{f'nx{i+1}':block[i] for i in range(3)},
                 'parthenon/output0':{'dt':end},output:{'dt':end}}
    if compression is not None:changes[output]['hdf5_compression_level']=compression
    (folder/'athinput').write_text(set_sections(text,changes))
    command=mpi_command({'ranks':ranks,'binary':binary})
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    peak=0;start=time.perf_counter();timed_out=False
    with (folder/'run.log').open('x') as log:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(p.memory_info().rss for p in handle.children(recursive=True)))
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            if time.perf_counter()-start>240:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)
                timed_out=True;break
            time.sleep(.1)
    before_sync=time.perf_counter()
    os.sync()
    wall=time.perf_counter()-start
    sync_seconds=time.perf_counter()-before_sync
    files=sorted(folder.glob('*.athdf' if code=='athpp' else '*.phdf'))
    log=(folder/'run.log').read_text()
    metrics=[s for s in log.splitlines() if any(w in s for w in ('zone-cycles','walltime used','time limit'))]
    r=dict(name=name,code=code,level=level,block=list(block),ranks=ranks,binary=binary,
           binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
           compression=compression,target_code_time=end,chi=100,wall_seconds=wall,flush_seconds=sync_seconds,
           peak_child_rss_gib=peak/1024**3,rc=proc.returncode,timed_out=timed_out,
           native_outputs=list(map(str,files)),native_bytes=sum(p.stat().st_size for p in files),metrics=metrics)
    (folder/'result.json').write_text(json.dumps(r,indent=2))
    print(json.dumps(r),flush=True)
    if r['rc'] or len(files)!=2:raise RuntimeError(name+' failed or missing native output')
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('suite',choices=['cpu_sweep','gpu_io','gpu_confirm','confirm']);a=p.parse_args()
    ROOT.mkdir(exist_ok=True)
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        lock=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
    if a.suite=='cpu_sweep':
        for name,block,binary in [('current',(64,64,64),OLD),('wide128',(128,64,32),OLD),
              ('wide256',(256,32,32),OLD),('small128',(128,32,32),OLD),
              ('small64',(64,64,32),OLD),('lto64',(64,64,64),LTO),('lto128',(128,64,32),LTO)]:
            run(name,block=block,binary=binary)
    elif a.suite=='gpu_io':
        for compression in (5,1,0):
            run(f'gpu_io_c{compression}',code='apk',level=6,block=(128,128,128),binary=APK,
                compression=compression,end=.32,ranks=1)
    elif a.suite=='gpu_confirm':
        for i in (2,3):
            for compression in (5,1):
                run(f'gpu_c{compression}_repeat{i}',code='apk',level=6,block=(128,128,128),binary=APK,
                    compression=compression,end=.32,ranks=1)
    else:
        candidates=[json.loads(f.read_text()) for f in (ROOT/'runs').glob('*/result.json')]
        candidates=[r for r in candidates if r['code']=='athpp' and r['level']==5 and r['rc']==0]
        best=min(candidates,key=lambda r:r['wall_seconds'])
        (ROOT/'selected_candidate.json').write_text(json.dumps(best,indent=2))
        for i in (2,3):
            run(f'current_repeat{i}')
            run(f'best_repeat{i}',block=best['block'],binary=best['binary'])
        run('L6_current',level=6,end=.24)
        run('L6_candidate',level=6,end=.24,block=best['block'],binary=best['binary'])

if __name__=='__main__':main()
