"""Prospectively specified 120-step output-observation diagnostics, not full controls."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
sys.path.insert(0,str(ROOT/'runner_instrumentation_v1'))
import gasoline_controls as g
WORK=ROOT/'longer_validation_v1'
RETAINED_SHA='7eb37f0ced056f78435b9f2c71883bf60c39ac78ee3948d6331a21204c222be3'
CASES=[('original_a',False,False),('original_b',False,False),
       ('retained_off',False,True),('retained_on',True,True)]


def spacing_limit(a,b,floor):
    """One binary32 spacing at a declared characteristic floor; no data edits."""
    scale=np.maximum(np.maximum(np.abs(a),np.abs(b)),floor).astype(np.float32)
    return np.spacing(scale).astype(np.float64)


def within_spacing(a,b,floor,period=None):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    direct=a-b
    d=direct if period is None else (direct+period/2)%period-period/2
    bound=spacing_limit(a,b,floor)
    return dict(passed=bool(np.all(abs(d)<=bound)),
                max_absolute=float(np.max(abs(d))),
                max_direct_absolute=float(np.max(abs(direct))),
                max_spacing_ratio=float(np.max(abs(d)/bound)),
                unequal=int(np.count_nonzero(direct)))


def measured_budget():
    # Every observed TIPSY state with all native sidecars, not just its .std size.
    sizes=[]
    for case in ('on_tanh','on_sharp'):
        base=ROOT/'instrumentation_v1'/case
        for name in ('state.initial','state.000003','state.000006'):
            sizes.append(sum(p.stat().st_size for p in base.iterdir()
                             if p.name==name or p.name.startswith(name+'.')))
    checkpoint=(ROOT/'instrumentation_v1/on_tanh/state.chk0').stat().st_size
    ic=(ROOT/'instrumentation_v1/on_tanh/ic.std').stat().st_size
    state_bound=max(8*1024**2,int(max(sizes)*1.25))
    per_case=int((22*state_bound+3*checkpoint+ic+256*1024**2)*1.25)
    return dict(measured_states_bytes=sizes,native_checkpoint_bytes=checkpoint,
        ic_bytes=ic,state_budget_bytes=state_bound,case_budget_bytes=per_case,
        all_four_cases_budget_bytes=4*per_case,
        formula='22 full states incl all sidecars + 3 checkpoints + IC + 256 MiB logs, then 25% margin per case',
        separate_each_filesystem_reserve=10*g.GIB)


def prepare():
    if WORK.exists():raise FileExistsError(WORK)
    b=measured_budget()
    for path in (ROOT,Path('/mnt/c')):
        if shutil.disk_usage(path).free < b['all_four_cases_budget_bytes']+10*g.GIB:
            raise RuntimeError('Complete diagnostic set does not fit '+str(path))
    g.budget()
    assert g.sha(ROOT/'native_retained/gasoline/gasoline')==RETAINED_SHA
    WORK.mkdir()
    old=g.params((ROOT/'instrumentation_v1/original_tanh/run.param').read_text())
    p=dict(old,nSteps='120',iOutInterval='6')
    # Exact strings below are inherited, never replaced with rounded physical guesses.
    assert p['iCheckInterval']=='60' and p['dDelta']==old['dDelta']
    items=[]
    for name,initial,retained in CASES:
        folder=WORK/name;folder.mkdir()
        shutil.copy2(ROOT/'instrumentation_v1/original_tanh/ic.std',folder/'ic.std')
        with (folder/'run.param').open('x') as f:
            f.write('# Native 120-step prospective output/retention diagnostic, not a full science control.\n')
            f.writelines(f'{k} = {v}\n' for k,v in p.items())
        binary=ROOT/'native_retained/gasoline/gasoline' if retained else ROOT/'gasoline_original'
        item=dict(name=name,law='tanh13',hook=initial,keep_checkpoints=retained,
             binary=str(binary),binary_sha256=g.sha(binary),ic_sha256=g.sha(folder/'ic.std'),
             parameter_sha256=g.sha(folder/'run.param'))
        g.write_new(folder/'native_environment.json',dict(
          GASOLINE_CLOUD_INITIAL_OUTPUT='1' if initial else None,
          GASOLINE_CLOUD_KEEP_CHECKPOINTS='1' if retained else None,
          PKDGRAV_CHECKPOINT_FDL=str(ROOT/'native/gasoline/checkpoint.fdl')))
        items.append(item)
    result=dict(status='prepared_prospective_120_step_diagnostics',full_science_controls_completed=0,
        native_states_expected=81,cases=items,budget=b,old_dDelta=old['dDelta'],
        protocol_sha256=g.sha(ROOT/'LONGER_VALIDATION_PLAN.md'))
    g.write_new(WORK/'preparation.json',result)
    return result


def checkpoints(folder,retained):
    files=sorted(folder.glob('state.step*.chk')) if retained else sorted(folder.glob('state.chk*'))
    if len(files)!=2:raise ValueError('Expected two checkpoints without overwriting')
    records=[]
    for path in files:
        before=g.sha(path)
        data=json.loads(subprocess.check_output([str(ROOT/'checkpoint_probe'),str(path)],text=True))
        assert data['valid']==1 and data['version']==8 and data['count']==65536
        assert path.stat().st_size==data['particle_offset']+65536*120
        assert g.sha(path)==before
        records.append(dict(path=str(path),sha256=before,bytes=path.stat().st_size,header=data))
    assert sorted(r['header']['step'] for r in records)==[60,120]
    return records


def run():
    bundle=json.loads((ROOT/'runner_longer_v1/bundle.json').read_text())
    for path,want in bundle['pinned_files'].items():assert g.sha(path)==want,path
    prep=json.loads((WORK/'preparation.json').read_text())
    if (WORK/'batch.json').exists():raise FileExistsError('Completed diagnostics must not be relaunched')
    g.WORK=WORK
    results=[]
    with g.locks():
        for item in prep['cases']:
            if item['keep_checkpoints']:os.environ['GASOLINE_CLOUD_KEEP_CHECKPOINTS']='1'
            else:os.environ.pop('GASOLINE_CLOUD_KEEP_CHECKPOINTS',None)
            result=g.run_case(item)
            result['checkpoints']=checkpoints(WORK/item['name'],item['keep_checkpoints'])
            g.write_new(WORK/item['name']/'checkpoint_validation.json',result['checkpoints'])
            results.append(result)
        g.write_new(WORK/'batch.json',dict(status='native_diagnostics_finished_pending_field_validation',
                                         cases=results,full_science_controls_completed=0))
    os.environ.pop('GASOLINE_CLOUD_KEEP_CHECKPOINTS',None)
    return dict(status='native_diagnostics_finished_pending_field_validation',cases=len(results))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run'])
    a=ap.parse_args();print(json.dumps(prepare() if a.action=='prepare' else run(),indent=2))
