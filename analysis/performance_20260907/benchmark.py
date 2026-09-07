"""Short, serial CPU/GPU benchmarks. Same numerical controls within each solver.

Each benchmark has two native outputs, not 101 production outputs. All native
test files are retained. This script never touches a production run directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import psutil
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/audit_20260907')
from grid_smokes import set_sections
from run_corrected_athpp import make_input

ROOT=Path('/home/kaan/performance_20260907')


def run_case(name,kind,binary,ranks,block,steps=32,level=5,end_time=.25,timeout_seconds=300):
    folder=ROOT/'benchmarks_v3'/name
    if (folder/'result.json').exists():
        previous=json.loads((folder/'result.json').read_text())
        if previous['returncode'] or len(previous['native_outputs'])<2:
            raise RuntimeError('Previous benchmark failed; use a new test name')
        return previous
    folder.mkdir(parents=True,exist_ok=False)
    if kind=='athpp':
        text=make_input(level,100).split('<output3>')[0]
        text=set_sections(text,{'time':{'nlim':100000,'tlim':end_time,'ncycle_out':100},
          'output1':{'dt':end_time},'output2':{'dt':end_time},
          'meshblock':{'nx1':block,'nx2':block,'nx3':block}})
    else:
        text=Path('/home/kaan/ic_audit_20260907/grid_tests/apk_chi100/athinput').read_text()
        # Keep all physical/numerical controls, replacing only benchmark duration/decomposition.
        nx=8*2**level
        text=set_sections(text,{'parthenon/mesh':{'nx1':nx//2,'nx2':nx,'nx3':nx//2},
          'parthenon/meshblock':{'nx1':block,'nx2':block,'nx3':block},
          'parthenon/time':{'nlim':100000,'tlim':end_time,'ncycle_out':100},
          'parthenon/output0':{'dt':end_time},'parthenon/output1':{'dt':end_time}})
    (folder/'athinput').write_text(text)
    mpi=['mpirun','--bind-to','core','-np',str(ranks)]
    if ranks==16:mpi=['mpirun','--use-hwthread-cpus','--bind-to','hwthread','--map-by','hwthread','-np','16']
    cmd=mpi+[str(binary),'-i','athinput']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    peak=0;started=time.perf_counter();gpu_samples=[];last_gpu=-10;timed_out=False
    with (folder/'run.log').open('x') as log:
        proc=subprocess.Popen(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:
                children=handle.children(recursive=True)
                peak=max(peak,sum(p.memory_info().rss for p in children if p.is_running()))
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            elapsed=time.perf_counter()-started
            if kind=='apk' and elapsed-last_gpu>=2:
                last_gpu=elapsed
                try:
                    smi=subprocess.run(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3)
                    gpu_samples.append({'elapsed':elapsed,'device_total_used_mib_and_util_percent':smi.stdout.strip()})
                except subprocess.TimeoutExpired:pass
            if elapsed>timeout_seconds:
                # Stop only this benchmark's separately created process group.
                import signal
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)
                timed_out=True
                break
            time.sleep(.25)
        rc=proc.wait()
    wall=time.perf_counter()-started
    raw=(folder/'run.log').read_text()
    metrics={}
    for line in raw.splitlines():
        if any(k in line.lower() for k in ('zone-cycles','walltime','wall time','zone cycles')):
            metrics[str(len(metrics))]=line
    files=sorted(folder.glob('*.athdf' if kind=='athpp' else '*.phdf'))
    result={'name':name,'kind':kind,'binary':str(binary),'binary_sha256':hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
       'ranks':ranks,'block':block,'target_time_code':end_time,'cycle_cap':100000,'dimensions_streamwise':[8*2**level,4*2**level,4*2**level],
       'chi':100,'returncode':rc,'wall_seconds_with_initialization_and_output':wall,
       'peak_summed_child_rss_gib':peak/1024**3,'native_outputs':list(map(str,files)),
       'timed_out':timed_out,'gpu_samples_device_wide':gpu_samples,
       'solver_metrics':metrics,'scope':'short benchmark; not science production; two outputs intended'}
    temporary=folder/'result.json.tmp'
    temporary.write_text(json.dumps(result,indent=2))
    temporary.replace(folder/'result.json')
    print(json.dumps(result),flush=True)
    if rc or len(files)<2:raise RuntimeError(f'{name} failed or has insufficient native output')
    return result


if __name__=='__main__':
    import fcntl
    suite_lock=(ROOT/'benchmark.lock').open('a')
    fcntl.flock(suite_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    p=argparse.ArgumentParser();p.add_argument('suite',choices=['cpu','gpu','confirm','gpu_confirm','l6','l6_gpu_retry','gpu128_clean']);a=p.parse_args()
    old='/home/kaan/ic_audit_20260907/bin/athpp';new=str(ROOT/'bin/athpp_native')
    if a.suite=='cpu':
        for name,binary,ranks,block in [('base32_r8',old,8,32),('native32_r8',new,8,32),
              ('native64_r8_retry',new,8,64),('native32_r16',new,16,32),('native64_r16',new,16,64),('native32_r4',new,4,32)]:
            try:run_case(name,'athpp',binary,ranks,block)
            except RuntimeError as e:print(str(e),flush=True)
    elif a.suite=='gpu':
        for block in (16,32,64):run_case(f'apk_block{block}','apk','/home/kaan/ic_audit_20260907/bin/apk',1,block,64)
    elif a.suite=='confirm':
        previous=[json.loads(f.read_text()) for f in (ROOT/'benchmarks_v3').glob('native*/result.json')]
        previous=[d for d in previous if d['returncode']==0 and len(d['native_outputs'])>=2]
        best=min(previous,key=lambda d:d['wall_seconds_with_initialization_and_output'])
        for repeat in (2,3):
            run_case(f'base32_r8_repeat{repeat}','athpp',old,8,32)
            run_case(f'best_repeat{repeat}','athpp',new,best['ranks'],best['block'])
    elif a.suite=='gpu_confirm':
        for repeat in (2,3):
            for block in (32,64):run_case(f'apk_block{block}_repeat{repeat}','apk','/home/kaan/ic_audit_20260907/bin/apk',1,block)
    elif a.suite=='gpu128_clean':
        run_case('apk_block128_clean','apk','/home/kaan/ic_audit_20260907/bin/apk',1,128)
        run_case('L6_apk_block128_clean','apk','/home/kaan/ic_audit_20260907/bin/apk',1,128,level=6,end_time=.08,timeout_seconds=120)
    elif a.suite=='l6_gpu_retry':
        for block in (64,32):
            try:run_case(f'L6_apk_block{block}_retry','apk','/home/kaan/ic_audit_20260907/bin/apk',1,block,level=6,end_time=.08,timeout_seconds=120)
            except RuntimeError as e:print(str(e),flush=True)
    else:
        run_case('L6_cpu_base','athpp',old,8,32,level=6,end_time=.08)
        run_case('L6_cpu_native','athpp',new,16,64,level=6,end_time=.08)
        run_case('L6_apk_block32','apk','/home/kaan/ic_audit_20260907/bin/apk',1,32,level=6,end_time=.08)
        run_case('L6_apk_block64','apk','/home/kaan/ic_audit_20260907/bin/apk',1,64,level=6,end_time=.08)
