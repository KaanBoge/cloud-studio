"""Native smoke of the production output/restart configuration, in new test dirs."""
import json
import os
from pathlib import Path
import subprocess
import run_optimized as r
profiles=json.loads((r.HERE/'optimized_profiles.json').read_text())
results=[]
for code in ('athpp','apk'):
    profile=profiles[f'{code}_L5']
    folder=r.WORK/'schedule_smokes'/code
    folder.mkdir(parents=True,exist_ok=False)
    text=r.input_for(code,5,100,profile['block'])
    sections=({'time':{'tlim':.001},**{f'output{i}':{'dt':.001} for i in (1,2,3)}} if code=='athpp' else
         {'parthenon/time':{'tlim':.001},**{f'parthenon/output{i}':{'dt':.001} for i in (0,1,2)}})
    (folder/'athinput').write_text(r.set_sections(text,sections))
    with (folder/'run.log').open('x') as log:
        rc=subprocess.run(r.mpi_command(profile),cwd=folder,stdout=log,stderr=subprocess.STDOUT,
             env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'),timeout=120).returncode
    fields=sorted(folder.glob('*.athdf' if code=='athpp' else '*.phdf'))
    restarts=sorted(folder.glob('*.rst' if code=='athpp' else '*.rhdf'))
    result=dict(code=code,returncode=rc,native_outputs=list(map(str,fields)),
                restart_files=list(map(str,restarts)),passed=rc==0 and len(fields)>=2 and len(restarts)>=2,
                scope='short output/restart write smoke, not a completed production run or checkpoint-read test')
    print(json.dumps(result),flush=True);results.append(result)
    if not result['passed']:raise AssertionError(result)
(r.HERE/'schedule_smokes.json').write_text(json.dumps(results,indent=2))
