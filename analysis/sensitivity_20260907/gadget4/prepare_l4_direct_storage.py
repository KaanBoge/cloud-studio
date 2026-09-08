"""Freeze a new full L4 runner and copy existing ICs; no native solver runs."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import psutil

SOURCE = Path(__file__).resolve().parent
BASE = Path('/home/kaan/sensitivity_20260907/gadget4')
DEST = BASE/'runner_full_l4_ntfs_v1'
RAW = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/gadget4_L4_velocity_pair_v1')
GIB = 1024**3


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if DEST.exists() or RAW.exists():
        raise FileExistsError('Existing preparation/run must be retained, never overwritten')
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        h=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        locks.append(h)
    proof_path=BASE/'validation_l4_v1/report.json'
    proof=json.loads(proof_path.read_text())
    assert proof['status']=='passed_L4_initial_and_short_evolved_mass_checks'
    assert sha(proof_path)==sha(SOURCE/'l4_validation.json')
    original=BASE/'runner_validation_l4_v2'
    assert sha(original/'bundle.json')==proof['frozen_bundle_sha256']
    old_bundle=json.loads((original/'bundle.json').read_text())
    for path,digest in old_bundle['pinned_files'].items():
        assert sha(path)==digest, path
    files={name:SOURCE/name for name in ('run_l4_direct_storage.py','test_l4_direct_storage.py',
               'prepare_l4_direct_storage.py','L4_DIRECT_STORAGE_PLAN.md')}
    for name in ('gadget_l4_controls.py','native_cadence.py'):
        files[name]=original/name
    # Controls import this existing base module; pin it and its recorded dependencies.
    sys.path.insert(0,str(BASE))
    from gadget_controls import dependencies,metadata,parameters,EXPECTED_BINARY
    dependencies()
    p=metadata()
    if psutil.virtual_memory().available<12*GIB:
        raise RuntimeError('Insufficient available guest RAM')
    DEST.mkdir()
    for name,path in files.items():
        shutil.copy2(path,DEST/name)
        if sha(path)!=sha(DEST/name):
            raise ValueError('Frozen copy mismatch')
    sys.path.insert(0,str(DEST))
    import run_l4_direct_storage as run
    run.no_competing_solver()
    run.verify_paths()
    before=run.inspect_storage(run.PAIR_BYTES)
    tests=subprocess.run([sys.executable,str(DEST/'test_l4_direct_storage.py')],
                         capture_output=True,text=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
    if tests.returncode:
        raise RuntimeError(tests.stdout+tests.stderr)
    RAW.mkdir(parents=True)
    (RAW/'scratch').mkdir()
    probe=RAW/'storage_probe.bin'
    with probe.open('xb') as stream:
        stream.write(bytes(range(256))*256)
        stream.flush()
        os.fsync(stream.fileno())
    if probe.read_bytes()!=bytes(range(256))*256:
        raise ValueError('Mounted byte readback failed')
    pins={str(DEST/name):sha(DEST/name) for name in files}
    pins.update({str(path):sha(path) for path in (BASE/'gadget_controls.py',BASE/'build.json',
                BASE/'experiment.json',BASE/'params_L4.txt',BASE/'Gadget4_pair',proof_path,
                Path('/home/kaan/verified_20260907/storage_guard.py'))})
    windows_files={'storage_probe.bin':sha(probe)}
    for case in proof['cases']:
        law='tanh13' if case['mode'] else 'sharp13'
        old_ic=Path(case['directory'])/'ics.hdf5'
        assert sha(old_ic)==case['ic_sha256']
        assert case['binary_sha256']==EXPECTED_BINARY
        folder=RAW/law
        folder.mkdir()
        shutil.copy2(old_ic,folder/'ics.hdf5')
        assert sha(folder/'ics.hdf5')==case['ic_sha256']
        values=run.input_values((BASE/'params_L4.txt').read_text(),p)
        with (folder/'params.txt').open('x') as out:
            out.write(''.join(f'{k:34s} {v}\n' for k,v in values.items()))
        for name in ('ics.hdf5','params.txt'):
            pins[str(folder/name)]=sha(folder/name)
            windows_files[f'{law}/{name}']=sha(folder/name)
        pins[str(old_ic)]=case['ic_sha256']
    assert sha(RAW/'sharp13/params.txt')==sha(RAW/'tanh13/params.txt')
    assert proof['full_pair_budget']['pair_bytes']==run.PAIR_BYTES
    plan=dict(status='frozen_reviewed_ready_for_windows_readback',physics=p,pins=pins,
              windows_readback_files=windows_files,tests=dict(returncode=tests.returncode,
              output=tests.stdout+tests.stderr),native_validation_report_sha256=sha(proof_path),
              source_plan_sha256=sha(DEST/'L4_DIRECT_STORAGE_PLAN.md'),
              storage_before=before,storage_after=run.inspect_storage(run.PAIR_BYTES),
              unchanged_native_retention_budget=proof['full_pair_budget'],
              guest_ancillary_allowance=run.GUEST_ALLOWANCE,
              source_binary=EXPECTED_BINARY,raw_destination=str(RAW),
              native_solver_runs_started=0,existing_raw_copied_moved_deleted=0,
              scope='Only two validated IC copies and small new runner/probe files prepared. No old raw relocation, no native experiment repeated.')
    with (DEST/'plan.json').open('x') as out:
        json.dump(plan,out,indent=2,allow_nan=False)
        out.write('\n')
    with (RAW/'preparation.json').open('x') as out:
        json.dump(plan,out,indent=2,allow_nan=False)
        out.write('\n')
    print(json.dumps(dict(status=plan['status'],plan_path=str(DEST/'plan.json'),
                         plan_sha256=sha(DEST/'plan.json'),tests_passed=15,
                         raw_destination=str(RAW),storage=plan['storage_after']),indent=2))


if __name__=='__main__':
    main()
