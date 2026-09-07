import json
import subprocess
from pathlib import Path
from check_snapshot import check
root=Path('/home/kaan/ic_audit_20260907')
controls=[('apk',root/'binary_before/athenaPK','*.phdf'),
          ('athpp',Path('/home/kaan/codes/athenapp/bin/athena_tanhvel_backup'),'*.athdf')]
results=[]
for kind,binary,pattern in controls:
    run=root/'negative_controls'/kind
    run.mkdir(parents=True,exist_ok=False)
    (run/'athinput').write_text((root/'grid_tests'/f'{kind}_chi1000'/'athinput').read_text())
    with (run/'run.log').open('x') as log:
        rc=subprocess.run(['mpirun','-np','1',str(binary),'-i','athinput'],cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
    if rc:
        raise RuntimeError(f'Control solver failed: {run}')
    result=check(str(sorted(run.glob(pattern))[0]),str(run/'athinput'),kind,[0,0,0],(64,32,32))
    result['expected_result']='FAIL: old initializer has the wrong velocity law'
    results.append(result)
    print(kind,result['passed'],result['errors'])
(root/'negative_controls/results.json').write_text(json.dumps(results,indent=2))
assert all(not r['passed'] and r['errors']['velocity_error_over_vwind_max']>.05 for r in results)
