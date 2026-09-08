"""One guarded six-step serial-output diagnostic; never a production queue."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
import psutil

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
BASE=ROOT/'native_retained'
TREE=ROOT/'serial_observer_native_v2'
OUT=ROOT/'serial_observer_runner_v2'
CASE=ROOT/'serial_observer_case_v2'
PY='/home/kaan/venv/bin/python'
GIB=1024**3
FILES=('serial_observer_run_v2.py','test_serial_observer_run_v2.py','serial_observer_v2.h',
       'test_serial_observer_v2.c','SERIAL_OBSERVER_PLAN.md','SERIAL_OBSERVER_PLAN_V2.md')
BASE_SHA='7eb37f0ced056f78435b9f2c71883bf60c39ac78ee3948d6331a21204c222be3'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)


def parameters(text):
    p={}
    for line in text.splitlines():
        line=line.split('#',1)[0].strip()
        if not line:continue
        k,v=(x.strip() for x in line.split('=',1))
        if k in p:raise ValueError('Duplicate native parameter')
        p[k]=v
    return p


def input_six(text):
    p=parameters(text)
    if p['nSteps']!='120' or p['iOutInterval']!='6' or p['iCheckInterval']!='60':
        raise ValueError('Unexpected retained diagnostic cadence')
    if p['bGasAdiabatic']!='1' or p['bGasCooling']!='0' or p['dExtraStore']!='0.2':
        raise ValueError('Unexpected native recipe')
    p['nSteps']='6'
    return ''.join(k+' = '+v+'\n' for k,v in p.items())


def records(log):
    if 'PKDGRAV_CHECKPOINT_FDL environment variable not set' in log:
        raise ValueError('Checkpoint retention disabled by missing environment')
    rows=[json.loads(line.split(' ',1)[1]) for line in log.splitlines()
          if line.startswith('CLOUD_SERIAL_OBSERVER ')]
    if [x.get('stage') for x in rows] != ['master_written','remote_written','master_restored']:
        raise ValueError('Missing/duplicate/out-of-order observer records')
    if not all(x.get('equal') is True for x in rows):
        raise ValueError('Native byte/count preservation failed')
    if rows[0]['count']+rows[1]['count']!=65536 or rows[0]['count']!=rows[2]['count']:
        raise ValueError('Incomplete particle population')
    if any(x['bytes']!=408*x['count'] for x in rows):
        raise ValueError('Unexpected native PARTICLE ABI')
    markers=[x for x in log.splitlines() if x.startswith('CLOUD_INITIAL_NATIVE_OUTPUT ')]
    if markers!=['CLOUD_INITIAL_NATIVE_OUTPUT time=0 file=state.initial']:
        raise ValueError('Wrong initialized output context')
    return rows


def check_environment(env):
    if env.get('GASOLINE_CLOUD_INITIAL_OUTPUT')!='1' or env.get('GASOLINE_CLOUD_KEEP_CHECKPOINTS')!='1':
        raise ValueError('Required native output settings missing')
    fdl=env.get('PKDGRAV_CHECKPOINT_FDL')
    if not fdl or not Path(fdl).is_file():raise ValueError('Native checkpoint schema unavailable')
    return env


def resources(preflight=True):
    if not os.path.ismount('/mnt/c') or os.stat('/mnt/c').st_dev==os.stat('/').st_dev:
        raise RuntimeError('Windows backing-volume measurement unavailable')
    guest=shutil.disk_usage(ROOT).free
    host=shutil.disk_usage('/mnt/c').free
    ram=psutil.virtual_memory().available
    if min(guest,host)<(11 if preflight else 10)*GIB or ram<(12 if preflight else 2)*GIB:
        raise RuntimeError('Observer retention/RAM guard')
    return dict(guest_free=guest,host_free=host,ram_available=ram)


@contextlib.contextmanager
def locks():
    with contextlib.ExitStack() as stack:
        for name in ('benchmark','production'):
            f=stack.enter_context(open('/home/kaan/performance_20260907/'+name+'.lock','a'))
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def subprocess_checked(cmd,log,cwd=None,timeout=300,env=None):
    with Path(log).open('x') as f:
        result=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    if result.returncode:raise RuntimeError('Command failed; preserved log '+str(log))


def build():
    if OUT.exists() or CASE.exists():raise FileExistsError('Do not reuse observer stages')
    if sha(BASE/'gasoline/gasoline')!=BASE_SHA:raise ValueError('Retained build changed')
    if not TREE.exists():raise FileNotFoundError('New source tree not prepared')
    initial_resources=resources()
    OUT.mkdir()
    here=Path(__file__).resolve().parent
    for name in FILES:shutil.copyfile(here/name,OUT/name)
    if sha(OUT/'serial_observer_v2.h')!=sha(TREE/'gasoline/serial_observer_v2.h'):
        raise ValueError('Native observer header differs from tested header')
    pinned={str(OUT/name):sha(OUT/name) for name in FILES}
    original={str(path.relative_to(BASE)):sha(path) for path in BASE.rglob('*') if path.is_file()}
    for rel,h in original.items():
        if rel=='gasoline/master.c':continue
        if sha(TREE/rel)!=h:raise ValueError('Unexpected copied source difference '+rel)
    before={str(path):sha(path) for path in TREE.rglob('*') if path.is_file()}
    with locks():
        subprocess_checked(['gcc','-std=gnu89','-O3','-Wall','-Wextra',
            str(OUT/'test_serial_observer_v2.c'),'-o',str(OUT/'observer_synthetic')],OUT/'synthetic_build.log',timeout=30)
        subprocess_checked([str(OUT/'observer_synthetic')],OUT/'synthetic_tests.log',timeout=10)
        subprocess_checked([PY,'-B',str(OUT/'test_serial_observer_run_v2.py')],OUT/'python_tests.log',timeout=30)
        subprocess_checked(['nice','-n','19','make','-j2','mpi'],OUT/'native_build.log',cwd=TREE/'gasoline')
    changed=[]
    for path,h in before.items():
        if sha(path)!=h:changed.append(str(Path(path).relative_to(TREE)))
    if sorted(changed)!=['gasoline/gasoline','gasoline/master.o']:
        raise ValueError('Unexpected native build changes '+str(changed))
    CASE.mkdir()
    origin=ROOT/'longer_validation_2rank_v1/retained_on'
    native_env=check_environment(json.loads((origin/'native_environment.json').read_text()))
    if sha(native_env['PKDGRAV_CHECKPOINT_FDL'])!=sha(TREE/'gasoline/checkpoint.fdl'):
        raise ValueError('Checkpoint schema differs from retained native recipe')
    input_text=input_six((origin/'run.param').read_text())
    with (CASE/'run.param').open('x') as f:f.write(input_text)
    shutil.copyfile(origin/'ic.std',CASE/'ic.std')
    for path in TREE.rglob('*'):
        if path.is_file():pinned[str(path)]=sha(path)
    for path in (origin/'run.param',origin/'ic.std',CASE/'run.param',CASE/'ic.std',
                 origin/'native_environment.json',Path(native_env['PKDGRAV_CHECKPOINT_FDL']),
                 ROOT/'checkpoint_probe',OUT/'python_tests.log',OUT/'synthetic_tests.log',OUT/'native_build.log'):
        pinned[str(path)]=sha(path)
    plan=dict(status='frozen_serial_observer_v2_ready',pins=pinned,base_tree=original,native_environment=native_env,
        native_changed_objects=changed,binary_sha256=sha(TREE/'gasoline/gasoline'),
        resource_budget_bytes=GIB,separate_reserve_each_bytes=10*GIB,
        preflight_resources=initial_resources,ranks=2,steps=6,
        scope='One new within-operation byte/count check, not an output-equivalence acceptance rerun.')
    save(OUT/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],binary_sha256=plan['binary_sha256'],changed=changed),indent=2))


def native_run(plan):
    if (CASE/'started.json').exists():raise FileExistsError('Native diagnostic already attempted')
    before_resources=resources()
    for path,h in plan['pins'].items():
        if sha(path)!=h:raise ValueError('Frozen evidence changed '+path)
    env=os.environ.copy()
    env.update(check_environment(plan['native_environment']))
    env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        GASOLINE_CLOUD_INITIAL_OUTPUT='1',GASOLINE_CLOUD_KEEP_CHECKPOINTS='1',
        GASOLINE_CLOUD_SERIAL_AUDIT='1')
    binary=TREE/'gasoline/gasoline'
    cmd=['nice','-n','19','mpirun','--bind-to','core','-np','2',str(binary),'run.param']
    samples=[];reason=None;stop_at=None
    with locks(),(CASE/'run.out').open('x') as log:
        start=time.monotonic()
        proc=subprocess.Popen(cmd,cwd=CASE,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(CASE/'started.json',dict(pid=proc.pid,command=cmd,binary_sha256=sha(binary),
                                    resources=before_resources,plan_sha256=sha(OUT/'plan.json')))
        while proc.poll() is None:
            elapsed=time.monotonic()-start
            rss=0;cpu=0.
            try:
                children=psutil.Process(proc.pid).children(recursive=True)
                for child in children:
                    try:
                        if child.exe()==str(binary):
                            rss+=child.memory_info().rss
                            ct=child.cpu_times();cpu+=ct.user+ct.system
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            except psutil.NoSuchProcess:pass
            samples.append([elapsed,rss,cpu])
            if reason is None:
                try:resources(preflight=False)
                except Exception as exc:reason=repr(exc)
                if elapsed>60:reason='60 second native cap'
                if reason:
                    with (CASE/'STOP').open('x') as f:f.write('1\n')
                    stop_at=time.monotonic()
            if stop_at is not None and time.monotonic()-stop_at>10:
                if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:
                            os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.05)
        rc=proc.wait(timeout=5);elapsed=time.monotonic()-start
    rates=[]
    for a,b in zip(samples,samples[1:]):
        if a[1]>0 and b[1]>0 and b[2]>=a[2] and b[0]>a[0]:
            rates.append((b[2]-a[2])/(b[0]-a[0]))
    result=dict(exit_code=rc,wall_seconds=elapsed,guard=reason,samples=samples,
        peak_solver_rss_bytes=max(x[1] for x in samples),
        median_busy_cpu_workers=float(np.median(rates)) if rates else None,ranks=2,gpu_used=False)
    save(CASE/'native_result.json',result)
    if rc or reason:raise RuntimeError('Observer native diagnostic failed')
    return result


def validate(result):
    sys.path.insert(0,str(ROOT/'runner_instrumentation_v1'))
    import gasoline_controls as g
    sys.path.insert(0,str(ROOT/'read_only_divergence_v1'))
    import review_divergence as r
    from yt.frontends.tipsy.api import TipsyDataset
    p=g.params((CASE/'run.param').read_text())
    log=(CASE/'run.out').read_text()
    rows=records(log)
    checkpoints=list(CASE.glob('state.step*.chk'))
    if len(checkpoints)!=1:raise ValueError('Expected one retained final step6 checkpoint')
    checkpoint=checkpoints[0]
    ch=json.loads(subprocess.check_output([str(ROOT/'checkpoint_probe'),str(checkpoint)],text=True,timeout=15))
    if ch['valid']!=1 or ch['version']!=8 or ch['step']!=6 or ch['count']!=65536:
        raise ValueError('Invalid terminal native checkpoint')
    if checkpoint.stat().st_size!=ch['particle_offset']+120*65536:
        raise ValueError('Incomplete terminal checkpoint payload')
    found={path.name for path in CASE.iterdir() if path.is_file() and
           (path.name=='state.initial' or (path.name.startswith('state.') and path.name[6:].isdigit()))}
    if found!={'state.initial','state.000006'}:raise ValueError('Unexpected native state population')
    terminal=0.
    for step in range(6):terminal+=float(p['dDelta'])
    if ch['time']!=terminal:raise ValueError('Checkpoint time does not match six native steps')
    design=json.loads((ROOT/'instrumentation_v1/preparation.json').read_text())
    chi=float(design['chi']);states=[]
    for name,want in [('state.initial',0.),('state.000006',terminal)]:
        path=CASE/name;t,a=r.tipsy(path)
        if t!=want or len(a)!=65536:raise ValueError('Native timestamp/count mismatch')
        direct=[float(a['mass'].astype(float).sum()),
                float(a['mass'][a['rho']>chi/3].astype(float).sum())]
        if name=='state.initial':
            ic=g.read(CASE/'ic.std')[1]
            for field in ('pos','vel','mass','temp','metals'):
                if not np.array_equal(ic[field],a[field]):raise ValueError('Initialized IC mismatch '+field)
        ds=TipsyDataset(str(path),parameter_file=str(CASE/'run.param'),
            bounding_box=[[-10,10],[-5,5],[-5,5]],
            index_filename=str(OUT/(name+'.index5')),kdtree_filename=str(OUT/(name+'.kdtree')))
        ds._periodicity=(False,False,False)
        ad=ds.all_data();m=ad['Gas','Mass'].to_value('code_mass').astype(float)
        rho=ad['Gas','Density'].to_value('code_mass/code_length**3').astype(float)
        independent=[float(m.sum()),float(m[rho>chi/3].sum())]
        rel=[abs(x-y)/max(abs(x),1) for x,y in zip(direct,independent)]
        if max(rel)>1e-12:raise ValueError('Independent mass mismatch')
        states.append(dict(path=str(path),sha256=sha(path),time_code=t,count=len(a),
                           direct_mass=direct,yt_mass=independent,relative_difference=rel))
    report=dict(status='passed_observed_serial_particle_bytes_not_trajectory_equivalence',
        full_controls_added=0,accepted_study_total=46,old_field_gate_still_failed=True,
        observer_records=rows,native_states=states,native_result=result,
        checkpoint=dict(path=str(checkpoint),sha256=sha(checkpoint),header=ch),
        plan_sha256=sha(OUT/'plan.json'),all_case_files={str(x):sha(x) for x in CASE.iterdir() if x.is_file()},
        limitations=['Only byte/count equality inside this instrumented serial writer is demonstrated.',
            'Not all process state, caches, communication order, timing or trajectory equivalence.',
            'Instrumentation may itself alter timing; unchanged arithmetic objects are not a no-effect proof.',
            'No extra repeat, changed tolerance, production viewer entry or full science control.'])
    for path,h in json.loads((OUT/'plan.json').read_text())['pins'].items():
        if sha(path)!=h:raise ValueError('Frozen input/source changed after diagnostic '+path)
    for rel,h in json.loads((OUT/'plan.json').read_text())['base_tree'].items():
        if sha(BASE/rel)!=h:raise ValueError('Original retained source tree changed '+rel)
    save(OUT/'report.json',report)
    print(json.dumps(dict(status=report['status'],records=rows,native_states=len(states),
                         wall_seconds=result['wall_seconds'],peak_solver_rss_bytes=result['peak_solver_rss_bytes']),indent=2))


def main():
    mode=argparse.ArgumentParser();mode.add_argument('--build',action='store_true');mode.add_argument('--run',action='store_true')
    args=mode.parse_args()
    if args.build==args.run:raise ValueError('Choose exactly one stage')
    if args.build:build();return
    if (OUT/'report.json').exists() or (OUT/'failure.json').exists() or (CASE/'started.json').exists():
        raise FileExistsError('Preserve completed or attempted native observer')
    plan=json.loads((OUT/'plan.json').read_text())
    if plan['status']!='frozen_serial_observer_v2_ready':raise ValueError('Not a frozen validated observer')
    try:validate(native_run(plan))
    except Exception as exc:
        save(OUT/'failure.json',dict(status='observer_stopped_needs_review',error=repr(exc),full_controls_added=0))
        raise


if __name__=='__main__':main()
