"""Fresh Gadget-4 L4 pair, existing validated ICs, direct C: raw storage.

No native rebuild, completed-run replay, raw relocation/deletion, or auto-resume.
"""
import fcntl
import json
import os
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
import shutil

import numpy as np
import psutil

HERE = Path(__file__).resolve().parent
BASE = Path('/home/kaan/sensitivity_20260907/gadget4')
RAW = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/gadget4_L4_velocity_pair_v1')
RESERVE = 10 * 1024**3
GUEST_ALLOWANCE = 1024**3
PAIR_BYTES = 7840595890
CASE_BYTES = 3920297945
PROOF_HASH = None  # the frozen plan pins the actual completed validation report

from gadget_l4_controls import input_values, paired_nonvelocity, verify_rows
from gadget_controls import sha, save, parameters, metadata, dependencies, read, CONFIG, EXPECTED_BINARY, GIB
from storage_guard import windows_backing_volume


def require(ok, message):
    if not ok:
        raise ValueError(message)


def mapping_gate(mount, host, output_device, guest_device):
    require(mount['target'] == '/mnt/c' and mount['source'] == 'C:\\'
            and mount['fstype'] == '9p' and 'aname=drvfs;path=C:\\;' in mount['options']
            and 'rw' in mount['options'].split(','), 'Unreviewed mounted Windows output mapping')
    require(host['drive'] == 'C:' and output_device != guest_device, 'Wrong backing drive or output device')


def budget_gate(guest_free, mounted_free, windows_free, remaining):
    for x in (guest_free, mounted_free, windows_free, remaining):
        require(type(x) is int and x >= 0, 'Invalid storage measurement/budget')
    require(guest_free >= RESERVE + GUEST_ALLOWANCE, 'Guest ancillary/reserve budget fails')
    require(min(mounted_free, windows_free) >= RESERVE + GUEST_ALLOWANCE + remaining,
            'Windows full-remaining-pair/ancillary/reserve budget fails')


def inspect_storage(remaining=0, live=False):
    parent = Path('/mnt/c/Users/kaanb/CloudCrushing')
    require(parent.resolve() == parent and BASE.resolve() == BASE, 'Unexpected root symlink')
    rows = json.loads(subprocess.check_output(['findmnt', '-J', '-T', str(parent),
                                               '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS'], text=True))['filesystems']
    require(len(rows) == 1, 'Ambiguous output mount')
    host = windows_backing_volume()
    mapping_gate(rows[0], host, parent.stat().st_dev, BASE.stat().st_dev)
    guest = shutil.disk_usage(BASE).free
    mounted = shutil.disk_usage(parent).free
    if live:
        require(min(guest, mounted, host['free_bytes']) >= RESERVE, 'Live host/guest reserve fails')
    else:
        budget_gate(guest, mounted, host['free_bytes'], remaining)
    return dict(guest_free_bytes=guest, mounted_free_bytes=mounted, windows=host,
                output_mount=rows[0], remaining_raw_budget=remaining, live_guard=live)


def no_competing_solver():
    names = ('athena', 'flash4', 'flashx', 'enzo', 'ramses', 'gizmo', 'gadget4', 'gasoline', 'arepo')
    found = []
    for proc in psutil.process_iter(['pid', 'name']):
        if any((proc.info['name'] or '').lower().startswith(n) for n in names):
            found.append(proc.info)
    require(not found, 'Existing native solver: ' + str(found))


def verify_paths():
    expected = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/gadget4_L4_velocity_pair_v1')
    require(RAW == expected and RAW.resolve() == RAW, 'Unexpected raw path or symlink')
    for ancestor in (RAW, *list(RAW.parents)[:-1]):
        require(not ancestor.is_symlink(), 'Raw ancestor is a symlink')


def check_pins(plan):
    for path, digest in plan['pins'].items():
        require(sha(path) == digest, 'Pinned dependency/input changed: ' + path)
    require(sha(BASE / 'Gadget4_pair') == EXPECTED_BINARY, 'Native executable changed')
    dependencies()


def safe_stop(proc, identity, folder):
    if proc.poll() is not None:
        return
    require(psutil.Process(proc.pid).create_time() == identity, 'PID ownership changed')
    output = folder / 'output'
    output.mkdir(exist_ok=True)
    (output / 'stop').touch(exist_ok=False)
    try:
        proc.wait(timeout=50)
        return
    except subprocess.TimeoutExpired:
        pass
    for sig, grace in ((signal.SIGTERM, 15), (signal.SIGKILL, 15)):
        if proc.poll() is not None:
            return
        require(psutil.Process(proc.pid).create_time() == identity
                and os.getpgid(proc.pid) == proc.pid, 'Process group ownership changed')
        os.killpg(proc.pid, sig)
        try:
            proc.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            pass
    raise RuntimeError('Owned solver did not stop after bounded grace')


def run_case(mode, plan):
    law = 'tanh13' if mode else 'sharp13'
    folder = RAW / law
    require(not (folder / 'result.json').exists() and not (folder / 'output').exists(),
            'Existing full case cannot be resumed')
    p = plan['physics']
    check_pins(plan)
    inspect_storage(CASE_BYTES * (2 if mode == 0 else 1))
    require(psutil.virtual_memory().available >= 12 * GIB, 'RAM preflight fails')
    ic, _ = read(folder / 'ics.hdf5')
    values = input_values((BASE / 'params_L4.txt').read_text(), p)
    require(parameters((folder / 'params.txt').read_text()) == values, 'Full numerical parameters changed')
    command = ['mpirun', '--bind-to', 'core', '-np', '8', str(BASE / 'Gadget4_pair'), 'params.txt']
    record = dict(status='running', code='Gadget-4 SPH', level=4, mode=mode,
                  directory=str(folder), physics=p, command=command,
                  binary_sha256=EXPECTED_BINARY, input_sha256=sha(folder/'params.txt'),
                  ic_sha256=sha(folder/'ics.hdf5'), storage=inspect_storage(live=True),
                  gpu_solver=False, start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    save(folder / 'result.json', record)
    print('START ' + str(folder), flush=True)
    start = time.monotonic()
    peak, previous, busy = 0, {}, []
    sample_at = guard_at = start
    proc = None
    with (folder/'run.log').open('x') as log, (folder/'resources.jsonl').open('x') as resources:
        try:
            proc = subprocess.Popen(command, cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True, env=dict(os.environ,
                                    OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                                    TMPDIR=str(RAW/'scratch')))
            handle = psutil.Process(proc.pid)
            identity = handle.create_time()
            record.update(mpirun_pid=proc.pid, mpirun_create_time=identity)
            save(folder/'result.json', record)
            while proc.poll() is None:
                now, rss, delta, current = time.monotonic(), 0, 0.0, {}
                try:
                    for child in handle.children(recursive=True):
                        try:
                            rss += child.memory_info().rss
                            cpu = child.cpu_times()
                            key = (child.pid, child.create_time())
                            current[key] = cpu.user + cpu.system
                            if key in previous:
                                delta += max(0, current[key]-previous[key])
                        except psutil.NoSuchProcess:
                            pass
                except psutil.NoSuchProcess:
                    pass
                cores = delta / max(now-sample_at, 1e-6)
                if previous:
                    busy.append(cores)
                peak = max(peak, rss)
                available = psutil.virtual_memory().available
                resources.write(json.dumps(dict(elapsed_seconds=now-start, rss_bytes=rss,
                    available_bytes=available, busy_cpu_cores=cores))+'\n')
                resources.flush()
                previous, sample_at = current, now
                require(available >= 2*GIB and now-start <= 6000, 'RAM/runtime guard')
                if now-guard_at >= 30:
                    inspect_storage(live=True)
                    guard_at = time.monotonic()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
        except BaseException as exc:
            if proc is not None and proc.poll() is None:
                safe_stop(proc, identity, folder)
            record.update(status='stopped_needs_review', error=repr(exc),
                          returncode=proc.returncode if proc else None, wall_seconds=time.monotonic()-start)
            save(folder/'result.json', record)
            raise
    record.update(status='solver_finished_pending_validation', returncode=proc.returncode,
                  wall_seconds=time.monotonic()-start, peak_child_rss_gib=peak/GIB,
                  median_busy_cpu_workers=statistics.median(busy) if busy else None)
    save(folder/'result.json', record)
    try:
        require(proc.returncode == 0, 'Native run failed')
        text = (folder/'run.log').read_text()
        require(all(flag in text for flag in CONFIG)
                and 'INIT: Hsml seed uses mean gas particle mass' in text, 'Native runtime provenance mismatch')
        rows, initial, _, schedule = verify_rows(folder, p, ic, values)
        require(len(rows) == 101, 'Unexpected native state count; preserve and review')
        restarts = sorted((folder/'output/restartfiles').glob('restart.*'))
        require(len(restarts) == 8, 'Unexpected retained restart generations')
        check_pins(plan)
        record.update(status='complete_independent_checks', series=rows, initial_checks=initial,
                      cadence=schedule, retained_restarts=[dict(path=str(x), bytes=x.stat().st_size,
                                                               sha256=sha(x)) for x in restarts])
        save(folder/'result.json', record)
    except BaseException as exc:
        record.update(status='needs_review', error=repr(exc))
        save(folder/'result.json', record)
        raise
    print(f"FINISH L4 {law}: {len(rows)} native states; {record['wall_seconds']:.1f}s; "
          f"median {record['median_busy_cpu_workers']:.2f} busy CPU workers; peak {peak/GIB:.3f}GiB", flush=True)
    return record


def main():
    verify_paths()
    require(not (RAW/'batch.json').exists(), 'Existing batch cannot be restarted')
    locks = []
    for name in ('benchmark.lock', 'production.lock'):
        handle = Path('/home/kaan/performance_20260907', name).open('a')
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(handle)
    no_competing_solver()
    plan = json.loads((HERE/'plan.json').read_text())
    require(plan['status'] == 'frozen_reviewed_ready_for_windows_readback', 'Unreviewed full plan')
    check_pins(plan)
    windows = json.loads((RAW/'windows_readback.json').read_text(encoding='utf-8-sig'))
    require(windows['plan_sha256'] == sha(HERE/'plan.json'), 'Windows proof has wrong plan')
    require(set(windows['hashes']) == set(plan['windows_readback_files']), 'Incomplete Windows file readback')
    for name, digest in windows['hashes'].items():
        require(digest == sha(RAW/name) == plan['windows_readback_files'][name], 'Windows/Linux readback mismatch')
    inspect_storage(PAIR_BYTES)
    require(psutil.virtual_memory().available >= 12*GIB, 'RAM preflight fails')
    batch = dict(status='running', plan_sha256=sha(HERE/'plan.json'), physics=plan['physics'],
                 whole_pair_budget=PAIR_BYTES, raw_storage=str(RAW), finished=[], new_full_controls=0)
    save(RAW/'batch.json', batch)
    # Reader temporaries also belong to the direct-storage allocation.
    os.environ['TMPDIR'] = str(RAW/'scratch')
    import tempfile
    tempfile.tempdir = str(RAW/'scratch')
    try:
        for mode in (0, 1):
            batch['active_directory'] = str(RAW/('tanh13' if mode else 'sharp13'))
            save(RAW/'batch.json', batch)
            batch['finished'].append(run_case(mode, plan))
            save(RAW/'batch.json', batch)
        a, b = batch['finished']
        require(a['input_sha256'] == b['input_sha256'], 'Paired numerical parameters differ')
        paired_nonvelocity(read(Path(a['directory'])/'ics.hdf5')[0], read(Path(b['directory'])/'ics.hdf5')[0])
        paired_nonvelocity(read(a['series'][0]['snapshot'])[0], read(b['series'][0]['snapshot'])[0])
        batch.update(status='complete_independent_pair_checks', new_full_controls=2)
        batch.pop('active_directory', None)
    except BaseException as exc:
        batch.update(status='stopped_needs_review', error=repr(exc))
        raise
    finally:
        save(RAW/'batch.json', batch)
    print('PAIR COMPLETE: two new native L4 controls; analysis and publication still pending.', flush=True)


if __name__ == '__main__':
    main()
