"""Bounded corrected 3D batch: Athena++/AthenaPK, L4, Mach 2, three chi.

Uses hash-pinned corrected executables and existing lossless numerical settings.
L4 timing is not benchmarked: no claim that an L5 speedup transfers to L4.
No cleanup, publishing, historical restart, cooling, or frame tracking.
"""
import argparse
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, '/home/kaan/performance_20260907')
sys.path.insert(0, '/home/kaan/verified_20260907')
import run_optimized as r

WORK = Path('/home/kaan/restart_20260907')
PLAN = [(code, chi) for chi in (10, 100, 1000) for code in ('athpp', 'apk')]
STEM = 'RESTART_sharp13_20260907_L4'


def save(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False))
    temporary.replace(path)


def profile_for(code, level=4):
    if level not in (3, 4, 5, 6):
        raise ValueError('Only verified integer ladder profiles are enabled')
    p = copy.deepcopy(json.loads((r.HERE/'optimized_profiles.json').read_text())[code+f'_L{max(5,level)}'])
    if level < 5:
        p.update(level=level, block=2**(level+1))
        p['lower_level_timing'] = 'Not benchmarked; reuses corrected binary, not the L5 timing claim.'
        # Lower-level inputs deliberately retain their original output encoding.
        # An L5-only IO optimization must not silently relabel their provenance.
        for key in ('hdf5_compression_level','io_scope','io_regression','io_timing','directory_prefix'):
            p.pop(key,None)
    return p


def validate_fields(target, code, tcc):
    import h5py
    import numpy as np
    rows = []
    for path in target.glob('*.athdf' if code == 'athpp' else '*.phdf'):
        with h5py.File(path) as f:
            t = float(f.attrs['Time'] if code == 'athpp' else f['Info'].attrs['Time'])
            data = f['prim'][...]
            if not np.all(np.isfinite(data)):
                raise ValueError('Nonfinite native fields: '+str(path))
            if code == 'athpp':
                raw_names = f.attrs['VariableNames']
                names = [x.decode() if isinstance(x, bytes) else str(x) for x in raw_names]
                density, pressure = data[names.index('rho')], data[names.index('press')]
            else:
                # Native Parthenon prim: blocks, 6 variables, k, j, i.
                if data.ndim != 5 or data.shape[1] != 6:
                    raise ValueError('Unexpected AthenaPK primitive layout')
                density, pressure = data[:, 0], data[:, 4]
            if np.min(density) <= 0 or np.min(pressure) <= 0:
                raise ValueError('Nonpositive density or pressure: '+str(path))
        if not math.isfinite(t) or t < 0:
            raise ValueError('Invalid native output time')
        rows.append((t/tcc, path.name))
    rows.sort()
    unique, duplicates = [], []
    for t, name in rows:
        if unique and abs(t-unique[-1][0]) < 1e-10:
            duplicates.append((t, name))
        else:
            unique.append((t, name))
    ts = np.array([x[0] for x in unique])
    complete = len(ts) == 101 and abs(ts[0]) < 1e-10 and abs(ts[-1]-5) < 1e-8
    # Output events are written on native integration steps, not exact requested
    # times. Record deviations; never relabel them as perfectly synchronized.
    offsets = ts-np.linspace(0, 5, 101) if len(ts) == 101 else None
    nominal = offsets is not None and bool(np.max(np.abs(offsets)) < 1e-5)
    ordered_cadence = offsets is not None and bool(np.all(offsets >= -1e-8) and np.all(offsets < .05))
    return dict(complete_outputs=bool(complete and ordered_cadence), unique_snapshots=len(ts),
                native_time_rows=rows, duplicate_time_files_retained=duplicates,
                exact_nominal_times=nominal,
                max_time_offset_tcc=None if offsets is None else float(np.max(np.abs(offsets))),
                finite_positive_fields=True,
                comparison_status='Provisional. Actual times differ; BC/tracer matching and retention need review.')


def run_case(code, chi, level=4):
    if level not in (3,4):
        raise ValueError('Use the prepared optimized launcher for L5/L6')
    p = profile_for(code, level)
    r.check_proof(p, chi)
    target = r.ROOTS[code]/f'RESTART_sharp13_20260907_L{level}_chi{chi}'
    if target.exists():
        # Never silently turn a crashed run into a new t=0 run.
        raise RuntimeError('Existing directory requires explicit review: '+str(target))
    disk, ram = r.budgets(p)
    storage = r.storage_snapshot(r.ROOTS[code])
    r.require_storage(storage, disk)
    available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines()
                         if x.startswith('MemAvailable:')))*1024
    if available < ram:
        raise RuntimeError('Insufficient RAM headroom')
    if code == 'apk':
        free = int(subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi',
            '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True).strip())
        if free < 2600:
            raise RuntimeError('Insufficient GPU headroom')
    text = r.input_for(code, level, chi, p['block'])
    if '<cooling>' in text or 'galilean_shift = true' in text:
        raise ValueError('Unsupported physics in fixed-frame batch')
    target.mkdir()
    (target/'athinput').write_text(text)
    physical = r.parse_file(target/'athinput')
    if not (math.isclose(physical['chi'], chi) and math.isclose(physical['mach'], 2)
            and math.isclose(physical['tmax']/physical['t_cc'], 5)
            and math.isclose(physical['output_dt']/physical['t_cc'], .05)):
        raise ValueError('Native parameter readback mismatch')
    dims = [8*2**level,4*2**level,4*2**level]
    record = dict(status='running', code=code, level=level, chi=chi, dimensions_streamwise=dims,
                  target_snapshots=101, physical_parameters=physical, profile=p,
                  binary_sha256=p['binary_sha256'], parameter_sha256=r.sha(target/'athinput'),
                  command=r.mpi_command(p), storage_preflight=storage,
                  reserved_disk_gib=disk/r.GIB, reserved_ram_gib=ram/r.GIB,
                  raw_retention='All native fields, times and restart files retained.',
                  started_at_unix=time.time())
    save(target/'provenance.json', record)
    save(WORK/'current.json', dict(status='running', directory=str(target), **{k:record[k] for k in ('code','chi','level','started_at_unix')}))
    print('START '+str(target), flush=True)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with (target/'run.log').open('x') as log:
        proc = subprocess.Popen(record['command'], cwd=target, stdout=log,
                                stderr=subprocess.STDOUT, env=env)
        with (target/'resources.jsonl').open('x') as samples:
            while proc.poll() is None:
                sample = {'unix':time.time(), 'loadavg':os.getloadavg(),
                          'meminfo':Path('/proc/meminfo').read_text()}
                try:
                    sample['gpu'] = subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi',
                        '--query-gpu=utilization.gpu,memory.used,memory.free',
                        '--format=csv,noheader,nounits'], text=True, timeout=5).strip()
                except Exception as error:
                    sample['gpu_sampling_error'] = str(error)
                samples.write(json.dumps(sample)+'\n'); samples.flush()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: pass
        rc = proc.returncode
    record.update(returncode=rc, wall_seconds=time.time()-record['started_at_unix'], status='needs_review')
    save(target/'provenance.json', record)
    if rc != 0:
        raise RuntimeError(f'Native solver failed rc={rc}; retained {target}')
    record.update(validate_fields(target, code, physical['t_cc']))
    from check_snapshot import check
    first = target/record['native_time_rows'][0][1]
    ic = check(str(first), str(target/'athinput'), code, [0,0,0], dims)
    save(target/'initial_conditions.json', ic)
    if not ic['passed'] or not record['complete_outputs']:
        save(target/'provenance.json', record)
        raise RuntimeError('Output/IC validation needs review: '+str(target))
    record['status'] = 'finished_native_checks_passed'
    save(target/'provenance.json', record)
    print(f"FINISHED {code} chi={chi}: {record['unique_snapshots']} native times; {record['wall_seconds']:.1f}s", flush=True)
    return dict(code=code, chi=chi, level=level, directory=str(target),
                snapshots=record['unique_snapshots'], wall_seconds=record['wall_seconds'],
                max_time_offset_tcc=record['max_time_offset_tcc'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if not args.run:
        print(json.dumps(dict(plan=PLAN, level=4, dimensions=[128,64,64],
                              note='Prepare-only display; pass --run to execute sequentially.'), indent=2))
        return
    WORK.mkdir(exist_ok=True)
    if (WORK/'batch.json').exists():
        raise RuntimeError('Batch already attempted; review results before another launch')
    with (r.WORK/'production.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        batch = dict(status='running', started_at_unix=time.time(), pid=os.getpid(), planned=PLAN, finished=[])
        save(WORK/'batch.json', batch)
        try:
            for code, chi in PLAN:
                batch['finished'].append(run_case(code, chi))
                save(WORK/'batch.json', batch)
            batch['status'] = 'finished_native_checks_passed'
        except Exception as error:
            batch.update(status='stopped_needs_review', error=str(error))
            raise
        finally:
            batch['updated_at_unix'] = time.time()
            save(WORK/'batch.json', batch)
            save(WORK/'current.json', batch)


if __name__ == '__main__':
    main()
