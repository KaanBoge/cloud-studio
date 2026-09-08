"""Freeze and test the runner bundle without starting a full simulation."""
import fcntl,json,os,shutil,subprocess,sys
from pathlib import Path
from run_full_l3 import ROOT,MODULES,sha,save,storage_snapshot,require_storage,GIB

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    dest=ROOT/'runner_l3_v1'
    completing=sys.argv[1:]==['--complete-existing']
    if sys.argv[1:] and not completing:raise ValueError('Only --complete-existing is supported')
    if dest.exists() and (not completing or (dest/'bundle.json').exists()):raise ValueError('Frozen bundle already exists; review it rather than overwrite')
    require_storage(storage_snapshot(ROOT),GIB//20)
    dest.mkdir(exist_ok=completing);source=Path(__file__).parent
    for name in MODULES+('test_full_l3.py','test_smoke_gizmo.py','test_snapshot_timing.py'):
        if not (dest/name).exists():shutil.copy2(source/name,dest/name)
        if sha(source/name)!=sha(dest/name):raise ValueError('Bundle copy differs')
    evidence={}
    for relative in ('restart.c','run.c','allvars.h','system/system.c'):
        src=Path('/home/kaan/codes/gizmo')/relative;out=dest/(relative.replace('/','_')+'.evidence')
        if not out.exists():shutil.copy2(src,out)
        if sha(out)!=sha(src):raise ValueError('Native evidence changed')
        evidence[relative]=dict(path=str(out),sha256=sha(out))
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    test=subprocess.run([sys.executable,'-m','unittest','test_full_l3.py','test_smoke_gizmo.py','test_snapshot_timing.py'],
                        cwd=dest,env=env,capture_output=True,text=True,timeout=120)
    save(dest/'tests.json',dict(returncode=test.returncode,stdout=test.stdout,stderr=test.stderr))
    if test.returncode:raise RuntimeError('Frozen runner tests failed')
    # The setup process already owns both locks. Run only the read-only
    # preflight function in the child, not main() which would acquire them again.
    pre=subprocess.run([sys.executable,'-c','import json,run_full_l3; print(json.dumps(run_full_l3.preflight()))'],cwd=dest,env=env,capture_output=True,text=True,timeout=120)
    if pre.returncode:raise RuntimeError('Frozen preflight failed: '+pre.stderr)
    plan=json.loads(pre.stdout);save(dest/'preflight.json',plan)
    save(dest/'bundle.json',dict(status='tested_ready_for_guarded_L3_launch',files={p.name:sha(p) for p in dest.glob('*.py')},
        native_scheduler_evidence=evidence,preflight_sha256=sha(dest/'preflight.json'),tests_sha256=sha(dest/'tests.json'),
        restart_policy='Native 3600-second per-rank CPU/wall timer; one regular generation plus final/stop generation before 6000+60s external limit. Native .bak retains the previous set. No restart is auto-resumed.',
        scope='Native L3 MFM/MFV only; full states will be validated after native completion. L4/L5 not enabled.'))
    print(json.dumps(dict(bundle=str(dest),status='tested_ready_for_guarded_L3_launch',tests=test.stderr,planned_controls=4,
        budgets=plan['budgets'],effective_free_gib=plan['storage']['effective_free_bytes']/GIB),indent=2))

if __name__=='__main__':main()
