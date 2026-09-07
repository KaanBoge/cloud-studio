"""Full native L5 IC checks at all chi for the candidate CPU production profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/performance_20260907')
from run_optimized import input_for,set_sections,mpi_command
sys.path.insert(0,'/home/kaan/verified_20260907')
from check_snapshot import check
root=Path('/home/kaan/performance_20260907b')
binary=root/'bin/athpp_lto'
results=[]
for chi in (10,100,1000):
    folder=root/'ic_tests'/f'athpp_chi{chi}'
    folder.mkdir(parents=True,exist_ok=False)
    text=input_for('athpp',5,chi,[128,64,32]).split('<output3>')[0]
    (folder/'athinput').write_text(set_sections(text,{'time':{'tlim':.001},'output1':{'dt':.001},'output2':{'dt':.001}}))
    with (folder/'run.log').open('x') as log:
        rc=subprocess.run(mpi_command({'ranks':16,'binary':str(binary)}),cwd=folder,stdout=log,stderr=subprocess.STDOUT,
            env=dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),timeout=90).returncode
    if rc:raise RuntimeError('Native IC smoke failed')
    initial=sorted(folder.glob('*.athdf'))[0]
    result=check(str(initial),str(folder/'athinput'),'athpp',[0,0,0],[256,128,128])
    result.update(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),solver_returncode=rc)
    (folder/'verification.json').write_text(json.dumps(result,indent=2))
    print(chi,result['passed'],result['errors'],flush=True);results.append(result)
    if not result['passed']:raise AssertionError(result)
Path(__file__).with_name('lto_ic_results.json').write_text(json.dumps(results,indent=2))
