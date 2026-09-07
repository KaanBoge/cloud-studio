"""Small isolated L5 speed probes. Never launches production or deletes data."""
import fcntl
import json
from pathlib import Path
import statistics
import sys
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/performance_20260907b')
import bench
import verify
sys.path.insert(0,'/home/kaan/verified_20260907')
from storage_guard import storage_snapshot,require_storage

ROOT=Path('/home/kaan/performance_20260907c')


def main():
    ROOT.mkdir(exist_ok=True)
    if (ROOT/'report.json').exists():
        raise RuntimeError('Already measured; do not silently repeat')
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        lock=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
    storage=storage_snapshot(ROOT)
    require_storage(storage,4*1024**3)
    bench.ROOT=ROOT
    rows={};checks=[]
    for i in range(1,4):
        for ranks in ((16,8) if i%2 else (8,16)):
            key=f'cpu_r{ranks}_{i}'
            rows[key]=bench.run(key,code='athpp',level=5,block=(128,64,32),
                binary=bench.LTO,end=.6,ranks=ranks)
        check=verify.compare_cpu(rows[f'cpu_r16_{i}'],rows[f'cpu_r8_{i}'])
        checks.append(dict(pair=[f'cpu_r16_{i}',f'cpu_r8_{i}'],**check))
        if not check['passed']:raise RuntimeError('CPU native-field mismatch')
    for i in range(1,4):
        for compression in ((5,1) if i%2 else (1,5)):
            key=f'gpu_c{compression}_{i}'
            rows[key]=bench.run(key,code='apk',level=5,block=(64,64,64),
                binary=bench.APK,compression=compression,end=.6,ranks=1)
        check=verify.compare_gpu(rows[f'gpu_c5_{i}'],rows[f'gpu_c1_{i}'])
        checks.append(dict(pair=[f'gpu_c5_{i}',f'gpu_c1_{i}'],**check))
        if not check['passed']:raise RuntimeError('GPU decoded-field mismatch')
    timing={}
    for family,old,new in [('CPU','cpu_r16','cpu_r8'),('GPU','gpu_c5','gpu_c1')]:
        before=statistics.median(rows[f'{old}_{i}']['wall_seconds'] for i in range(1,4))
        after=statistics.median(rows[f'{new}_{i}']['wall_seconds'] for i in range(1,4))
        timing[family]=dict(baseline_seconds=before,candidate_seconds=after,
            reduction_percent=100*(1-after/before),
            candidate_peak_rss_gib=max(rows[f'{new}_{i}']['peak_child_rss_gib'] for i in range(1,4)),
            native_bytes_ratio=statistics.median(rows[f'{new}_{i}']['native_bytes']/rows[f'{old}_{i}']['native_bytes'] for i in range(1,4)))
    report=dict(storage_preflight=storage,runs=rows,field_checks=checks,timing=timing,
        scope='Short L5 chi100 Mach2 tests through code time 0.6; two native dumps, not a 5 tcc run.',
        production_profiles_changed=False)
    (ROOT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(timing,indent=2),flush=True)


if __name__=='__main__': main()
