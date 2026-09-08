"""Freeze/test L4 orchestration without launching or touching native solver code."""
import fcntl,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
import mfm_l4_controls as m

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        h=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(h)
    m.dependencies(False);m.guard(6*m.GIB)
    dest=m.ROOT/'runner_mfm_l4_v1'
    if dest.exists():raise ValueError('Existing frozen bundle must not be overwritten')
    dest.mkdir()
    files={}
    for name in ('mfm_l4_controls.py','test_mfm_l4.py'):
        shutil.copy2(HERE/name,dest/name);files[name]=m.sha(dest/name)
    result=subprocess.run([sys.executable,'-m','unittest','test_mfm_l4'],cwd=dest,text=True,capture_output=True,
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
    m.save(dest/'tests.json',dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
    if result.returncode:raise RuntimeError('Frozen L4 tests failed: '+result.stderr)
    record=dict(status='tested_for_native_L4_validation_only',files=files,base_bundle_sha256=m.sha(m.BASE/'bundle.json'),
        build_sha256=m.sha(m.ROOT/'build.json'),tests_sha256=m.sha(dest/'tests.json'),
        scope='MFM L4 only. No full run admitted without per-level native/timing/independent checks and whole-pair storage budget. Native solver binaries, numerics and existing helper bundle are unchanged.')
    m.save(dest/'bundle.json',record);print(json.dumps(record,indent=2))

if __name__=='__main__':main()
