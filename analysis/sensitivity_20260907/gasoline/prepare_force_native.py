"""Prepare isolated native trace adapter. No simulation launch entry point."""
import argparse
from contextlib import ExitStack
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import psutil

ROOT=Path('/home/kaan/sensitivity_20260907/gasoline')
BASE=ROOT/'native_retained'
TREE=ROOT/'force_order_native_v1'
OUT=ROOT/'force_order_prepare_v1'
CORE=ROOT/'force_trace_core_v1'
PY='/home/kaan/venv/bin/python'
CHANGED=('gasoline/smooth.c','gasoline/smoothfcn.c','gasoline/SphPressureTerms.h')
GIB=1024**3


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)


def resources():
    if not os.path.ismount('/mnt/c') or os.stat('/mnt/c').st_dev==os.stat('/').st_dev:
        raise RuntimeError('Cannot identify host backing volume')
    free=dict(guest=shutil.disk_usage(ROOT).free,host=shutil.disk_usage('/mnt/c').free,
              ram=psutil.virtual_memory().available)
    if min(free['guest'],free['host'])<11*GIB or free['ram']<12*GIB:
        raise RuntimeError('Trace stage reserve unavailable')
    return free


def checked(command,log,cwd=OUT,timeout=30):
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with Path(log).open('x') as f:
        r=subprocess.run(command,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    if r.returncode:raise RuntimeError('Command failed; retained '+str(log))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--copy',action='store_true');ap.add_argument('--build',action='store_true')
    arg=ap.parse_args()
    if arg.copy==arg.build:raise ValueError('Choose one preparation stage')
    free=resources()
    if sha(BASE/'gasoline/gasoline')!='7eb37f0ced056f78435b9f2c71883bf60c39ac78ee3948d6331a21204c222be3':
        raise ValueError('Original retained executable changed')
    if sha(CORE/'report.json')!='69100849bf2cd4423d6f91bfcf82e887a87bff62bc1ffa4719ad8118eed772cb':
        raise ValueError('Completed core evidence changed')
    with ExitStack() as stack:
        for name in ('benchmark','production'):
            f=stack.enter_context(open('/home/kaan/performance_20260907/'+name+'.lock','a'))
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if arg.copy:
            if OUT.exists() or TREE.exists():raise FileExistsError('New native trace stage already exists')
            OUT.mkdir();shutil.copytree(BASE,TREE)
            original={str(p.relative_to(BASE)):sha(p) for p in BASE.rglob('*') if p.is_file()}
            for rel,h in original.items():
                if sha(TREE/rel)!=h:raise ValueError('Source copy differs '+rel)
            save(OUT/'copy_manifest.json',dict(original=original,resources=free,native_runs=0))
            print('Isolated native tree copied; no modifications or solver runs');return
        if (OUT/'build_manifest.json').exists() or (OUT/'failure.json').exists():
            raise FileExistsError('Preserve attempted/completed native preparation')
        manifest=json.loads((OUT/'copy_manifest.json').read_text())
        here=Path(__file__).resolve().parent
        names=('force_trace_native.h','test_force_trace_native.c','prepare_force_native.py','FORCE_ORDER_TRACE_DESIGN.md')
        for name in names:shutil.copyfile(here/name,OUT/name)
        for name in ('force_trace_core.h','force_trace_replay.py'):
            shutil.copyfile(CORE/name,OUT/name)
        for name in ('force_trace_native.h','force_trace_core.h'):
            shutil.copyfile(OUT/name,TREE/'gasoline'/name)
        pins={str(p):sha(p) for p in OUT.iterdir() if p.is_file()}
        added_lines={}
        for rel,h in manifest['original'].items():
            if sha(BASE/rel)!=h:raise ValueError('Original source changed '+rel)
            if rel in CHANGED:
                old=(BASE/rel).read_text().splitlines();new=(TREE/rel).read_text().splitlines()
                tags=difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes()
                if any(t[0] not in ('equal','insert') for t in tags):
                    raise ValueError('Original lines removed or replaced '+rel)
                added_lines[rel]=sum(t[4]-t[3] for t in tags if t[0]=='insert')
                if not added_lines[rel]:raise ValueError('Missing native instrumentation '+rel)
            elif sha(TREE/rel)!=h:raise ValueError('Unexpected copied change '+rel)
        before={str(p.relative_to(TREE)):sha(p) for p in TREE.rglob('*') if p.is_file()}
        save(OUT/'prebuild_plan.json',dict(pins=pins,native_before=before,original_lines_preserved=added_lines,
            resources=free,native_runs=0,scope='Build/adapter synthetic validation only; native runner pending'))
        try:
            checked(['nice','-n','19','gcc','-std=gnu89','-O3','-Wall','-Wextra','-Werror',
                     'test_force_trace_native.c','-lm','-o','adapter_test'],OUT/'adapter_compile.log')
            streams=[]
            for rank in (0,1):
                case=OUT/('synthetic_rank'+str(rank));case.mkdir()
                checked([str(OUT/'adapter_test'),str(rank)],case/'test.log',cwd=case)
                streams.append((case/('force.rank%02d.bin'%rank)).read_bytes())
            sys.path.insert(0,str(OUT));import force_trace_replay as replay
            synthetic=replay.validate_case(streams)
            checked(['nice','-n','19','make','-j2','mpi'],OUT/'native_build.log',cwd=TREE/'gasoline',timeout=300)
            after={str(p.relative_to(TREE)):sha(p) for p in TREE.rglob('*') if p.is_file()}
            changed=sorted(rel for rel,h in before.items() if after[rel]!=h)
            if changed!=['gasoline/gasoline','gasoline/smooth.o','gasoline/smoothfcn.o']:
                raise ValueError('Unexpected rebuilt objects '+repr(changed))
            for path,h in pins.items():
                if sha(path)!=h:raise ValueError('Frozen preparation source changed '+path)
            for rel,h in manifest['original'].items():
                if sha(BASE/rel)!=h:raise ValueError('Original changed after build '+rel)
            save(OUT/'build_manifest.json',dict(status='native_trace_adapter_built_not_run',
                native_runs=0,full_controls_added=0,accepted_study_total=46,
                native_runner_pending=True,trajectory_gate_cleared=False,synthetic=synthetic,
                original_lines_preserved=added_lines,changed_objects=changed,
                binary_sha256=after['gasoline/gasoline'],native_hashes=after,
                artifacts={str(p):sha(p) for p in OUT.rglob('*') if p.is_file()}))
            print(json.dumps(dict(status='native_trace_adapter_built_not_run',changed=changed,
                binary_sha256=after['gasoline/gasoline'],synthetic_record_counts=[r['records'] for r in synthetic['ranks']]),indent=2))
        except Exception as exc:
            save(OUT/'failure.json',dict(status='native_trace_preparation_failed',error=repr(exc),native_runs=0))
            raise


if __name__=='__main__':main()
