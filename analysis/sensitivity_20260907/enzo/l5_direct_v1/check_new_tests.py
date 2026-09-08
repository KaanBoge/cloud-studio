"""Run only the new L5 direct-storage wrapper tests and retain their result."""
import os
import subprocess
import sys
import runner as r

target=r.HERE/'test_result.json'
if target.exists():
    raise FileExistsError('Existing test record must be retained')
result=subprocess.run([sys.executable,str(r.HERE/'test_runner.py')],capture_output=True,text=True,
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
r.save(target,dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,
                  plan_sha256=r.sha(r.HERE/'plan.json')))
print(result.stdout+result.stderr,flush=True)
raise SystemExit(result.returncode)
