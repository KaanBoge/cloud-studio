"""Freeze/test the trace transport and replay only. Never launch a native solver."""
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
OUT=ROOT/'force_trace_core_v1'
BASE=ROOT/'native_retained/gasoline'
PY='/home/kaan/venv/bin/python'
GIB=1024**3
FILES=('force_trace_core.h','test_force_trace_core.c','force_trace_replay.py',
       'test_force_trace_replay.py','prepare_force_trace_core.py','FORCE_ORDER_TRACE_DESIGN.md')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False)


def checked(command,log,timeout=30):
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with Path(log).open('x') as f:
        result=subprocess.run(command,cwd=OUT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    if result.returncode:raise RuntimeError('Retained failed test: '+str(log))


def main():
    if OUT.exists():raise FileExistsError('Preserve existing trace-core stage')
    if not os.path.ismount('/mnt/c') or os.stat('/mnt/c').st_dev==os.stat('/').st_dev:
        raise RuntimeError('Cannot measure Windows backing volume')
    capacity=dict(guest=shutil.disk_usage(ROOT).free,host=shutil.disk_usage('/mnt/c').free,
                  available_ram=psutil.virtual_memory().available)
    if min(capacity['guest'],capacity['host'])<11*GIB or capacity['available_ram']<12*GIB:
        raise RuntimeError('Whole proposed-stage reserve is unavailable')
    if sha(BASE/'gasoline')!='7eb37f0ced056f78435b9f2c71883bf60c39ac78ee3948d6331a21204c222be3':
        raise ValueError('Retained executable identity changed')
    original={str(BASE/name):sha(BASE/name) for name in
        ('gasoline','smooth.c','smoothfcn.c','SphPressureTerms.h','floattype.h')}
    with ExitStack() as stack:
        for name in ('benchmark','production'):
            lock=stack.enter_context(open('/home/kaan/performance_20260907/'+name+'.lock','a'))
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        OUT.mkdir()
        here=Path(__file__).resolve().parent
        for name in FILES:shutil.copyfile(here/name,OUT/name)
        pins={str(OUT/name):sha(OUT/name) for name in FILES}
        plan=dict(status='frozen_synthetic_trace_core_only',pins=pins,native_source_pins=original,
                  resources=capacity,native_solver_runs=0,full_controls_added=0,
                  native_insertion_and_runner_pending=True)
        save(OUT/'plan.json',plan)
        start=time.monotonic()
        try:
            checked(['nice','-n','19','gcc','-std=gnu89','-O3','-Wall','-Wextra','-Werror',
                     'test_force_trace_core.c','-lm','-o','core_test'],OUT/'compile.log')
            checked([str(OUT/'core_test'),'core_trace.bin','overflow_trace.bin'],OUT/'c_tests.log')
            checked([PY,'-B','-m','unittest','-v','test_force_trace_replay'],OUT/'python_tests.log')
            sys.path.insert(0,str(OUT))
            import force_trace_replay as replay
            valid=replay.validate((OUT/'core_trace.bin').read_bytes())
            try:replay.validate((OUT/'overflow_trace.bin').read_bytes())
            except ValueError as exc:overflow_error=str(exc)
            else:raise ValueError('Incomplete C overflow trace was accepted')
            for path,h in {**pins,**original}.items():
                if sha(path)!=h:raise ValueError('Frozen or native source changed: '+path)
            size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
            if size>2*1024**2:raise RuntimeError('Synthetic stage exceeded 2 MiB artifact allowance')
            report=dict(status='passed_synthetic_trace_transport_and_replay',
                native_solver_runs=0,native_frames_added=0,full_controls_added=0,accepted_study_total=46,
                native_insertion_and_runner_pending=True,trajectory_gate_cleared=False,
                test_wall_seconds=time.monotonic()-start,artifact_bytes_before_report=size,
                c_trace_replay=valid,overflow_correctly_rejected=overflow_error,
                plan_sha256=sha(OUT/'plan.json'),
                artifacts={str(p):sha(p) for p in OUT.iterdir() if p.is_file()})
            save(OUT/'report.json',report)
            print(json.dumps({k:report[k] for k in ('status','native_solver_runs','native_frames_added',
                'native_insertion_and_runner_pending','test_wall_seconds','artifact_bytes_before_report')},indent=2))
        except Exception as exc:
            save(OUT/'failure.json',dict(status='synthetic_trace_core_failed',error=repr(exc),
                                        native_solver_runs=0,full_controls_added=0))
            raise


if __name__=='__main__':main()
