"""Isolated L3 Gasoline output-instrumentation validation, not a full run queue.

Preserves native TIPSY data, all sidecars, restarts and failed attempts.
Never count an input IC as a native initialized output.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
import psutil

ROOT = Path('/home/kaan/sensitivity_20260907/gasoline')
CANON = Path('/home/kaan/codes/gasoline')
WORK = ROOT / 'instrumentation_v1'
PY = '/home/kaan/venv/bin/python'
GIB = 1024**3
HEADER = np.dtype([('time','>f8'), ('nbodies','>i4'), ('ndim','>i4'),
                   ('nsph','>i4'), ('ndark','>i4'), ('nstar','>i4'), ('pad','>i4')])
GAS = np.dtype([('mass','>f4'), ('pos','>f4',3), ('vel','>f4',3),
                ('rho','>f4'), ('temp','>f4'), ('eps','>f4'), ('metals','>f4'), ('phi','>f4')])
CASES = [('original_tanh', 'tanh13', False, ROOT/'gasoline_original'),
         ('off_tanh', 'tanh13', False, ROOT/'native/gasoline/gasoline'),
         ('on_tanh', 'tanh13', True, ROOT/'native/gasoline/gasoline'),
         ('on_sharp', 'sharp13', True, ROOT/'native/gasoline/gasoline')]
ORIGINAL_SHA = 'c7645e1774fb4a18fc68bac615ba03f24c83d06dfe4addfbbbc7df2cc4930bb5'
HOOK_SHA = '7f3018e12f821fe9f74ae2617d80b11cf1e7f7feedd8040ceafc01822a21789e'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_new(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)


def params(text):
    result = {}
    for line in text.splitlines():
        line = line.split('#',1)[0].strip()
        if not line:
            continue
        key, val = (s.strip() for s in line.split('=',1))
        if key in result:
            raise ValueError('Duplicate parameter: '+key)
        result[key] = val
    return result


def read(path):
    path = Path(path)
    with path.open('rb') as f:
        raw = f.read(32)
        if len(raw) != 32:
            raise ValueError('Truncated TIPSY header')
        h = np.frombuffer(raw, HEADER)[0]
        n = int(h['nsph'])
        if n <= 0 or h['nbodies'] != n or h['ndim'] != 3 or h['ndark'] or h['nstar']:
            raise ValueError('Not a three-dimensional, all-gas TIPSY state')
        if path.stat().st_size != 32+48*n:
            raise ValueError('TIPSY payload size mismatch')
        a = np.fromfile(f, GAS, count=n)
    if not np.isfinite(h['time']):
        raise ValueError('Invalid time')
    for k in GAS.names:
        if not np.isfinite(a[k]).all():
            raise ValueError('Nonfinite '+k)
    for k in ('mass','rho','temp','eps'):
        if not (a[k] > 0).all():
            raise ValueError('Nonpositive '+k)
    return float(h['time']), a


def energy_factor(p):
    if 'dMsolUnit' in p or 'dKpcUnit' in p or int(p['bGasCooling']) != 0:
        raise ValueError('Unsupported thermodynamic convention')
    if int(p['bGasAdiabatic']) != 1:
        raise ValueError('Not adiabatic')
    return float(p['dGasConst'])/(float(p['dConstGamma'])-1)/float(p['dMeanMolWeight'])


def budget():
    guest = shutil.disk_usage(ROOT).free
    host = shutil.disk_usage('/mnt/c').free
    ram = psutil.virtual_memory().available
    if min(guest,host) < 11*GIB or ram < 12*GIB:
        raise RuntimeError('Short-test preflight: need 1 GiB scratch plus 10 GiB reserve and 12 GiB RAM')
    return dict(guest_free=guest,host_free=host,ram_available=ram,
                scratch_budget=GIB,separate_reserve=10*GIB)


@contextlib.contextmanager
def locks():
    with contextlib.ExitStack() as stack:
        for name in ('benchmark','production'):
            f = stack.enter_context(open('/home/kaan/performance_20260907/'+name+'.lock','a'))
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def prepare():
    if WORK.exists():
        raise FileExistsError(WORK)
    resource = budget()
    assert sha(ROOT/'gasoline_original') == ORIGINAL_SHA
    assert sha(CANON/'gasoline') == ORIGINAL_SHA
    assert sha(ROOT/'native/gasoline/gasoline') == HOOK_SHA
    WORK.mkdir()
    historical = CANON/'runs/CW3D_L3_chi100/ics_L3_chi100.std'
    template = params((CANON/'runs/CW3D_L3_chi100/cwL3c100.param').read_text())
    generated = {}
    for law in ('tanh13','sharp13'):
        dst = WORK/(law+'.std')
        cmd = [PY,str(ROOT/'generators'/law/'make_gasoline_cloudwind_3d.py'),
               '--chi','100','--dx','0.3125','--mass-mode','variable','--seed','42',
               '--rv-scale','1.3','--out',str(dst)]
        if dst.exists():
            raise FileExistsError(dst)
        with (WORK/(law+'_generator.log')).open('x') as log:
            subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        generated[law] = read(dst)[1]
    old = read(historical)[1]
    for k in GAS.names:
        if not np.array_equal(old[k],generated['tanh13'][k]):
            raise ValueError('Archived IC reconstruction mismatch: '+k)
        if k != 'vel' and not np.array_equal(generated['tanh13'][k],generated['sharp13'][k]):
            raise ValueError('Nonvelocity IC mismatch: '+k)
    assert len(old) == 65536
    assert not np.array_equal(generated['tanh13']['vel'],generated['sharp13']['vel'])
    rows = []
    for name,law,hook,binary in CASES:
        case = WORK/name
        case.mkdir()
        shutil.copy2(WORK/(law+'.std'),case/'ic.std')
        p = template.copy()
        # Explicitly output-only changes, identical across all four tests.
        p.update(achInFile='ic.std', achOutName='state', nSteps='6', iOutInterval='3',
                 bDoIOrderOutput='1', bDoPressureOutput='1')
        assert energy_factor(p) > 0
        allowed = {'achInFile','achOutName','nSteps','iOutInterval',
                   'bDoIOrderOutput','bDoPressureOutput'}
        assert all(k in allowed or p[k] == v for k,v in template.items())
        with (case/'run.param').open('x') as f:
            f.write('# Native L3 output instrumentation test; six original-size timesteps.\n')
            f.writelines(f'{k} = {v}\n' for k,v in p.items())
        rows.append(dict(name=name,law=law,hook=hook,binary=str(binary),
                         binary_sha256=sha(binary),ic_sha256=sha(case/'ic.std'),
                         parameter_sha256=sha(case/'run.param')))
    report = dict(status='prepared_short_instrumentation_tests_only',resources=resource,
                  original_historical_ic=str(historical),historical_sha256=sha(historical),
                  historical_all_arrays_exact=True,nonvelocity_pair_exact=True,
                  chi=100,mach=2,gamma=float(template['dConstGamma']),radius=1,
                  vwind=2*math.sqrt(float(template['dConstGamma'])),level=3,
                  lattice=[64,32,32],mass_mode='variable',seed=42,cases=rows)
    write_new(WORK/'preparation.json',report)
    return report


def validate_ranks(item):
    if item.get('ranks')!=2:
        raise ValueError('Historical Gasoline executor requires exactly two workers')


def run_case(item):
    validate_ranks(item)
    case = WORK/item['name']
    assert sha(item['binary']) == item['binary_sha256']
    assert sha(case/'ic.std') == item['ic_sha256']
    assert sha(case/'run.param') == item['parameter_sha256']
    if (case/'run_started.json').exists():
        raise FileExistsError('Do not relaunch '+str(case))
    resource = budget()
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
               PKDGRAV_CHECKPOINT_FDL=str(ROOT/'native/gasoline/checkpoint.fdl'))
    env.pop('GASOLINE_CLOUD_INITIAL_OUTPUT',None)
    if item['hook']:
        env['GASOLINE_CLOUD_INITIAL_OUTPUT']='1'
    cmd = ['mpirun','--bind-to','core','-np','2',item['binary'],'run.param']
    write_new(case/'run_started.json',dict(command=cmd,environment_overrides={
        k:env.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS',
        'PKDGRAV_CHECKPOINT_FDL','GASOLINE_CLOUD_INITIAL_OUTPUT')},resources=resource))
    peak=0; samples=[]; guard=None; stop_at=None
    start = time.monotonic()
    with (case/'run.out').open('x') as log:
        proc = subprocess.Popen(cmd,cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,
                                start_new_session=True)
        parent=psutil.Process(proc.pid)
        while proc.poll() is None:
            rss=0; cpu=0
            try:
                for p in parent.children(recursive=True):
                    try:
                        rss+=p.memory_info().rss
                        t=p.cpu_times(); cpu+=t.user+t.system
                    except psutil.Error:
                        pass
            except psutil.Error:
                pass
            now=time.monotonic();peak=max(peak,rss)
            samples.append([now-start,rss,cpu])
            if guard is None:
                try:
                    if min(shutil.disk_usage(ROOT).free,shutil.disk_usage('/mnt/c').free) < 10*GIB:
                        guard='storage reserve'
                    elif psutil.virtual_memory().available < 2*GIB:
                        guard='low available RAM'
                    elif now-start > 300:
                        guard='300-second short-test cap'
                except OSError:
                    guard='unavailable host storage'
                if guard:
                    (case/'STOP').touch(exist_ok=False)
                    stop_at=now
            if stop_at is not None and now-stop_at > 30:
                os.killpg(proc.pid,signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.15)
        rc=proc.wait()
    result=dict(name=item['name'],exit_code=rc,solver_seconds=time.monotonic()-start,
                peak_child_rss_bytes=peak,samples_elapsed_rss_cpu=samples,guard=guard,
                ranks=2,hardware='CPU-only native MPI',full_science_control=False)
    write_new(case/'solver_result.json',result)
    if rc != 0 or guard:
        raise RuntimeError('Preserved failed native test: '+item['name'])
    return result


def run():
    manifest=ROOT/'runner_instrumentation_v1/bundle.json'
    frozen=json.loads(manifest.read_text())
    for path,want in frozen['pinned_files'].items():
        assert sha(path)==want,('Frozen file changed',path)
    prep=json.loads((WORK/'preparation.json').read_text())
    with locks():
        outcomes=[]
        for item in prep['cases']:
            outcomes.append(run_case(item))
        write_new(WORK/'solver_batch.json',dict(status='native_short_tests_finished_not_yet_validated',
                                               cases=outcomes,full_controls_completed=0))
    return outcomes


if __name__ == '__main__':
    raise SystemExit('Import the guarded case executor from a separately frozen, reviewed diagnostic runner.')
