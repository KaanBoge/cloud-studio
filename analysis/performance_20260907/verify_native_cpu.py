"""Verify the new build at native t=0 for each chi; no production run."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, '/mnt/c/Users/kaanb/CloudCrushing/audit_20260907')
from check_snapshot import check
from grid_smokes import set_sections
from run_corrected_athpp import make_input

root=Path('/home/kaan/performance_20260907')
binary=root/'bin/athpp_native'
for chi in (10,100,1000):
    folder=root/'ic_tests'/f'athpp_chi{chi}'
    folder.mkdir(parents=True,exist_ok=False)
    text=set_sections(make_input(3,chi),{'time':{'tlim':.001,'nlim':2},
         'output1':{'dt':.001},'output2':{'dt':.001},'output3':{'dt':.001},
         'meshblock':{'nx1':16,'nx2':16,'nx3':16}})
    (folder/'athinput').write_text(text)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (folder/'run.log').open('x') as log:
        rc=subprocess.run(['mpirun','--bind-to','core','-np','2',str(binary),'-i','athinput'],
             cwd=folder,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=60).returncode
    if rc:raise RuntimeError('IC test solver failed')
    snapshot=sorted(folder.glob('*.athdf'))[0]
    result=check(str(snapshot),str(folder/'athinput'),'athpp',[0,0,0],(64,32,32))
    result.update(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),solver_returncode=rc)
    (folder/'verification.json').write_text(json.dumps(result,indent=2))
    print(chi,result['passed'],result['errors'],flush=True)
    if not result['passed']:raise AssertionError(result)
