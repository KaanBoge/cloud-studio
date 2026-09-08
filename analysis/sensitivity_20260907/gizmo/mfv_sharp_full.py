"""Only the missing full sharp control; reuse the verified historical native run."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

ROOT=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1')
PREP=ROOT/'sharp_prepare_runner_v1'
sys.path.insert(0,str(PREP))
import mfv_sharp_prepare as p

HERE=Path(__file__).resolve().parent
PACKAGE=ROOT/'sharp_full_runner_v1'
DEST=ROOT/'sharp_full_native_v1'
PREP_PLAN='74c54e9db5785752e3193e3130e5d2a3ae94474262ce6121b24e6564adbbe6e8'
PREP_REPORT='41933e9cee047882a0008fe9505e7790151daa7abcef3c619fc03a4699ba97da'


def prerequisites():
    p.check(p.sha(PREP/'plan.json')==PREP_PLAN and p.sha(p.DEST/'validation.json')==PREP_REPORT,'Preparation evidence changed')
    plan=json.loads((PREP/'plan.json').read_text());p.frozen(plan)
    report=json.loads((p.DEST/'validation.json').read_text())
    p.check(report['status']=='passed_sharp_preparation_not_full_pair' and report['historical_recipe_reusable'],'Preparation did not pass')
    for case in report['cases']:
        for row in case['outputs']+case['terminal']['files']:p.check(p.sha(row['path'])==row['sha256'],'Preparation raw changed')
    r=p.recipe();p.historical_hashes(r)
    return plan,r


def freeze():
    p.check(not PACKAGE.exists() and not DEST.exists(),'Full sharp attempt/package exists')
    prior,r=prerequisites();disk=p.storage_snapshot(ROOT);p.require_storage(disk,prior['potential_full_bytes']);p.no_competing()
    p.check(p.psutil.virtual_memory().available>12*p.GIB,'RAM preflight')
    PACKAGE.mkdir()
    names=['mfv_sharp_full.py','test_mfv_sharp_full.py','MFV_SHARP_FULL_PLAN.md']
    for name in names:shutil.copy2(HERE/name,PACKAGE/name)
    plan=dict(status='frozen_missing_sharp_only',files={n:p.sha(PACKAGE/n) for n in names},prep_plan_sha256=PREP_PLAN,
        prep_validation_sha256=PREP_REPORT,historical_review_sha256=p.HIST_REVIEW,physics=r['physics'],
        case_bytes=prior['potential_full_bytes'],storage=disk,binary_sha256=p.onset.EXPECTED_BINARY,
        ic_sha256=p.SHARP_IC,input_sha256=p.onset.EXPECTED_INPUT,wall_limit=600,stop_grace=30,ranks=8)
    with (PACKAGE/'tests.log').open('x') as log:
        subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_sharp_full'],cwd=PACKAGE,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    plan['tests_sha256']=p.sha(PACKAGE/'tests.log');p.save(PACKAGE/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],sha256=p.sha(PACKAGE/'plan.json'),budget_gib=plan['case_bytes']/p.GIB)))


def frozen(plan):
    p.check(HERE==PACKAGE,'Only frozen full runner may execute')
    for n,digest in plan['files'].items():p.check(p.sha(PACKAGE/n)==digest,'Frozen full helper changed')
    p.check(p.sha(PACKAGE/'tests.log')==plan['tests_sha256'],'Frozen full tests changed')
    return prerequisites()


def run(plan):
    frozen(plan);locks=[]
    try:
        for name in ('benchmark.lock','production.lock'):
            f=open('/home/kaan/performance_20260907/'+name,'a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
        result=p.run_native(DEST,(p.OLD/'params.txt').read_text(),p.OLD/'ics.hdf5',plan['case_bytes'],600,30,
            dict(plan_sha256=p.sha(PACKAGE/'plan.json'),reused_historical=str(p.HIST)))
        print(json.dumps(result))
    finally:
        for f in reversed(locks):f.close()


def mass_comparison(sharp,historical,tcc):
    p.check(len(sharp)>1 and len(historical)>1 and tcc>0,'Incomplete pair')
    denom=historical[0]['dense_mass'];p.check(denom>0 and sharp[0]['dense_mass']==denom,'Different initial denominators')
    series={}
    for name,rows in (('sharp',sharp),('historical',historical)):
        times=np.array([r['time_code']/tcc for r in rows]);m=np.array([r['dense_mass'] for r in rows])/denom
        p.check(np.isfinite(times).all() and np.isfinite(m).all() and (m>=0).all() and (np.diff(times)>=0).all(),'Invalid mass series')
        p.check(times[0]==0 and abs(times[-1]-5)<1e-12,'Mass series missing endpoint')
        series[name]=dict(native_times_tcc=times.tolist(),dense_mass_fraction=m.tolist())
    grid=np.linspace(0,5,101)
    # Only scalar diagnostics are interpolated. Raw states/times remain intact.
    curves={k:np.interp(grid,v['native_times_tcc'],v['dense_mass_fraction']) for k,v in series.items()}
    diff=np.abs(curves['sharp']-curves['historical']);index=int(np.argmax(diff))
    return dict(initial_dense_mass=denom,series=series,scalar_grid_tcc=grid.tolist(),
        maximum_absolute_separation_fraction=float(diff[index]),time_of_maximum_tcc=float(grid[index]),
        method='Native-time curves; peak uses explicit linear scalar interpolation onto0:0.05:5tcc. No3Dframe interpolation.',
        interpretation='One coarse L3 within-code sensitivity, not exact-solution error or convergence.')


def analyze(plan):
    _,r=frozen(plan);target=DEST/'pair_validation.json';p.check(not target.exists(),'Full validation already exists')
    p.check(p.sha(DEST/'ics.hdf5')==p.SHARP_IC and p.sha(DEST/'params.txt')==p.onset.EXPECTED_INPUT,'Full sharp input changed')
    initial,rows=p.audit_outputs(DEST,plan['physics']);params=p.short.parameters((DEST/'params.txt').read_text())
    histinitial,_=p.short.read_arrays(p.HIST/'output/snapshot_000.hdf5')
    matches=p.same_fields(initial,histinitial,('Velocities','ParticleVelocities'))
    ic,_=p.short.read_arrays(DEST/'ics.hdf5',False);term=p.terminal(DEST,params,ic,full=True)
    timing=p.cadence([x['time_code'] for x in rows],params)
    original=json.loads((p.HIST/'validation.json').read_text())
    p.check(p.sha(p.HIST/'validation.json')=='d1da6d9d1e5b356fb1dd10e8f34931f316e51529a4865a72442f5757dd7a1d76','Historical scalar provenance changed')
    histrows=original['outputs']
    p.check(all(not row['errors'] and max(row['independent_relative_errors'])<1e-11 for row in histrows),'Historical reader checks failed')
    p.cadence([x['time_code'] for x in histrows],params);p.historical_hashes(r)
    mass=mass_comparison(rows,histrows,r['tcc'])
    for row in rows+term['files']:p.check(p.sha(row['path'])==row['sha256'],'New raw changed after analysis')
    report=dict(status='passed_repaired_mfv_L3_pair',plan_sha256=p.sha(PACKAGE/'plan.json'),script_sha256=p.sha(__file__),
        binary_sha256=p.onset.EXPECTED_BINARY,physics=plan['physics'],sharp_outputs=rows,sharp_cadence=timing,
        sharp_terminal=term,initial_nonvelocity_exact=matches,historical_reused=True,
        historical_review_sha256=p.HIST_REVIEW,historical_outputs=histrows,historical_resources=original['resources'],
        sharp_resources=json.loads((DEST/'result.json').read_text()),mass_comparison=mass,
        accepted_full_controls_after_this_pair=46,new_accepted_controls=2,
        limitations=['One coarse initial64x32x32 lattice; finer resolution not validated.','Old failed uninitialized-timestep MFV controls remain excluded.',
            'Native velocities are staggered; no simultaneous velocity diagnostics.','Periodic boundaries and kernel-pressure deviations retained; no cross-code equality.',
            'No passive material-retention diagnostic, cooling or frame tracking.','Validated analysis is not new production3Dviewer entries or a raw backup.'])
    p.save(target,report);print(json.dumps(dict(status=report['status'],sharp_frames=len(rows),historical_frames=len(histrows),
        maximum_mass_separation_percent=100*mass['maximum_absolute_separation_fraction'],sha256=p.sha(target))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run','analyze']);mode=parser.parse_args().mode
    if mode=='freeze':freeze()
    else:
        plan=json.loads((PACKAGE/'plan.json').read_text())
        try:(run if mode=='run' else analyze)(plan)
        except BaseException as error:
            target=DEST/(mode+'_error.json')
            if DEST.exists() and not target.exists():p.save(target,dict(error=str(error),script_sha256=p.sha(__file__)))
            raise
