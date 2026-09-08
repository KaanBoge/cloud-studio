"""Recheck the same native smoke data, without rerunning a solver."""
import json
from pathlib import Path
import run_arepo as a

def main():
    batch=json.loads((a.ROOT/'smoke_batch_v2.json').read_text())
    if batch['status']!='complete_native_checks' or len(batch['finished'])!=2:raise ValueError('Native pair missing')
    checks=[]
    for case in batch['finished']:
        folder=Path(case['directory'])
        if a.sha(folder/'param.txt')!=case['native_input_sha256'] or a.sha(folder/'IC.hdf5')!=case['ic_sha256']:raise ValueError('Smoke input changed')
        data=a.validate(folder,case['physics'],case['level'],case['mode'],True)
        checks.append(dict(directory=str(folder),unique_times=data['unique_snapshots'],initial=data['series'][0]['native_initial_check']))
    result=dict(status='passed',launcher_sha256=a.sha(a.__file__),checks=checks,pair=a.pair_initial(*batch['finished']),
        caveat='Original jittered equal-volume IC gives nonuniform native Voronoi density/pressure. Same within pair, not a uniform-pressure or matched-all-code claim.',
        failed_attempt_preserved='smokes/ and smoke_batch.json: TimeMax .001 shorter than native MaxSizeTimestep .05; v2 extends smoke to .1 only.')
    a.save(a.ROOT/'setup_validation.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
