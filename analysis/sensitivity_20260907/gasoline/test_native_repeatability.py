"""Two NEW identical-original-binary six-step controls to measure repeat variability.

No change to the frozen instrumentation runner or any existing case. This is
a negative-control diagnostic, not another historical/sharp science pair.
"""
import json
from pathlib import Path
import shutil
import sys

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
sys.path.insert(0,str(ROOT/'runner_instrumentation_v1'))
import gasoline_controls as g

def main():
    frozen=json.loads((ROOT/'runner_instrumentation_v1/bundle.json').read_text())
    for path,want in frozen['pinned_files'].items():
        assert g.sha(path)==want,('Frozen file changed',path)
    dest=ROOT/'repeatability_v1'
    if dest.exists():raise FileExistsError(dest)
    g.budget()
    dest.mkdir()
    base=ROOT/'instrumentation_v1/original_tanh'
    items=[]
    for n in (1,2):
        name=f'original_repeat{n}'
        case=dest/name;case.mkdir()
        for file in ('ic.std','run.param'):
            shutil.copy2(base/file,case/file)
            assert g.sha(base/file)==g.sha(case/file)
        items.append(dict(name=name,law='tanh13',hook=False,
                          binary=str(ROOT/'gasoline_original'),binary_sha256=g.ORIGINAL_SHA,
                          ic_sha256=g.sha(case/'ic.std'),parameter_sha256=g.sha(case/'run.param')))
    g.write_new(dest/'preparation.json',dict(status='original_binary_negative_controls_only',
          comparison='Measure native repeat variation before attributing tiny differences to the output hook',
          original_case=str(base),cases=items))
    # Only the new work root changes; use the exact frozen, guarded case executor.
    g.WORK=dest
    with g.locks():
        results=[g.run_case(item) for item in items]
    g.write_new(dest/'solver_batch.json',dict(status='finished_negative_controls_pending_audit',
                                             cases=results,full_science_controls_completed=0))

if __name__=='__main__':main()
