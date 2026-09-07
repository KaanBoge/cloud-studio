"""Build isolated IC-sensitivity executables; no production source/binary writes.

Athena++ uses a separate source/object tree and its tested compiler options.
AthenaPK compiles only an isolated pgen, then links the existing immutable solver
objects/libraries with that one replacement. Every command and linked input hash
is recorded. Build failures leave all files for inspection.
"""
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

SRC = Path('/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
ROOT = Path('/home/kaan/sensitivity_20260907')
sys.path.insert(0, '/home/kaan/verified_20260907')
from storage_guard import storage_snapshot, require_storage, GIB


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def command(args, cwd, name):
    with (ROOT / (name+'_'+str(time.time_ns())+'.log')).open('x') as log:
        subprocess.run(['nice', '-n', '19']+args, cwd=cwd, stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=600)


def main():
    ROOT.mkdir(exist_ok=True)
    locks=[]
    for name in ('benchmark.lock', 'production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); locks.append(f)
    require_storage(storage_snapshot(ROOT), 2*GIB)
    if (ROOT/'build.json').exists():
        raise RuntimeError('Existing build evidence: review rather than overwrite')
    (ROOT/'bin').mkdir(exist_ok=True)
    result={'created_unix':time.time(), 'status':'building', 'codes':{}}

    app=Path('/home/kaan/codes/athenapp')
    tree=ROOT/'athpp_build'
    tree.mkdir(exist_ok=True)
    if not (tree/'src').exists():
        shutil.copytree(app/'src',tree/'src')
        shutil.copy2(app/'Makefile',tree/'Makefile')
    shutil.copy2(SRC/'source/athpp_cloud_wind.cpp',tree/'src/pgen/cloud_wind.cpp')
    args=['make','-j2','OBJ_DIR=obj/',f'EXE_DIR={ROOT}/bin/',
          f'EXECUTABLE={ROOT}/bin/athpp_pair',
          'CXXFLAGS=-O3 -march=native -fno-fast-math -ffp-contract=off -flto=2 -std=c++11 -I/usr/include/hdf5/openmpi']
    command(args,tree,'build_athpp')
    result['codes']['athpp']={'binary':str(ROOT/'bin/athpp_pair'),
        'binary_sha256':sha(ROOT/'bin/athpp_pair'), 'command':args,
        'source_manifest':{str(p.relative_to(tree)):sha(p) for p in sorted((tree/'src').rglob('*')) if p.is_file()}}
    (ROOT/'build.partial.json').write_text(json.dumps(result,indent=2))
    print('Built Athena++ sensitivity binary',flush=True)

    apk=Path('/home/kaan/codes/athenapk')
    build=apk/'build-cuda'
    apk_tree=ROOT/'apk_source'
    shutil.copytree(apk/'src',apk_tree)
    shutil.copy2(SRC/'source/apk_cloud.cpp',apk_tree/'pgen/cloud.cpp')
    commands=json.loads((build/'compile_commands.json').read_text())
    matches=[c for c in commands if c['file']==str(apk/'src/pgen/cloud.cpp')]
    if len(matches)!=1: raise RuntimeError('Ambiguous native compile command')
    entry=matches[0]; args=shlex.split(entry['command'])
    obj=ROOT/'apk_cloud.cpp.o'
    args[args.index('-o')+1]=str(obj)
    args[args.index('-c')+1]=str(apk_tree/'pgen/cloud.cpp')
    command(args,entry['directory'],'compile_apk_pgen')
    link=shlex.split((build/'src/CMakeFiles/athenaPK.dir/link.txt').read_text())
    old='CMakeFiles/athenaPK.dir/pgen/cloud.cpp.o'
    if link.count(old)!=1: raise RuntimeError('Expected exactly one cloud object')
    link[link.index(old)]=str(obj)
    link[link.index('-o')+1]=str(ROOT/'bin/apk_pair')
    link=[f'-Wl,--dependency-file={ROOT}/apk_link.d' if x.startswith('-Wl,--dependency-file=') else x for x in link]
    inputs={}
    for x in link[1:]:
        if x.startswith('-'): continue
        p=Path(x)
        if not p.is_absolute(): p=build/'src'/p
        if p.is_file(): inputs[str(p.resolve())]=sha(p)
    command(link,build/'src','link_apk')
    result['codes']['apk']={'binary':str(ROOT/'bin/apk_pair'),
        'binary_sha256':sha(ROOT/'bin/apk_pair'), 'compile_command':args,
        'link_command':link,'linked_input_sha256':inputs,
        'source_manifest':{str(p.relative_to(apk_tree)):sha(p) for p in sorted(apk_tree.rglob('*')) if p.is_file()}}
    for p,h in inputs.items():
        if sha(p)!=h: raise RuntimeError('A linked input changed during build: '+p)
    result['status']='built'
    (ROOT/'build.json').write_text(json.dumps(result,indent=2))
    print('Built AthenaPK sensitivity binary; production trees unchanged',flush=True)


if __name__=='__main__': main()
