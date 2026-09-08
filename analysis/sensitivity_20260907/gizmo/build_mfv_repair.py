"""Build isolated reference/one-assignment MFV candidates; never run a solver."""
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import psutil

ROOT = Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1')
CANON = Path('/home/kaan/codes/gizmo')
STUDY = ROOT.parent
GIB = 1024**3
INSERT = '    dt_hydrostep_i = local.dt_hydrostep_i;\n\n'
MARKER = '    /* certain particles should never enter the loop: check for these */'
PROBE_FLAGS = ['-g', '-O1', '-ffast-math', '-fcommon', '-Wall',
               '-Wuninitialized', '-Wmaybe-uninitialized', '-DDISABLE_ALIGNED_ALLOC',
               '-DCHIMES_USE_DOUBLE_PRECISION', '-DH5_USE_16_API',
               '-I/usr/include/hdf5/openmpi', '-I.']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def guard():
    for root in ['/', '/mnt/c']:
        require(shutil.disk_usage(root).free > 11*GIB, 'Build disk reserve: '+root)
    require(psutil.virtual_memory().available > 6*GIB, 'Build RAM reserve')


def command(argv, cwd, log):
    guard()
    start = time.monotonic()
    with log.open('xb') as stream:
        proc = subprocess.Popen(['nice', '-n', '19', *argv], cwd=cwd,
                                stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            while proc.poll() is None:
                guard()
                require(time.monotonic()-start < 600, 'Build/probe timeout')
                time.sleep(.5)
        except BaseException:
            os.killpg(proc.pid, 15)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, 9)
                proc.wait()
            raise
    require(proc.returncode == 0, 'Command failed; retained '+str(log))
    return dict(command=argv, seconds=time.monotonic()-start, log_sha256=sha(log))


def main():
    require(not (ROOT/'build_report.json').exists(), 'Completed build report exists')
    require(not (ROOT/'reference'/'GIZMO_reference').exists(), 'Build already attempted')
    manifest = json.loads((ROOT/'source_manifest.json').read_text())
    reference = (ROOT/'reference/hydro/hydro_evaluate.h').read_text()
    repaired = (ROOT/'repaired/hydro/hydro_evaluate.h').read_text()
    require(reference.count(MARKER) == 1, 'Source insertion not unique')
    require(repaired == reference.replace(MARKER, INSERT+MARKER), 'Not the one-assignment candidate')
    for row in manifest['source_files']:
        require(sha(CANON/row['path']) == row['sha256'], 'Canonical source changed')
        for variant in ['reference','repaired','mfm_probe']:
            if variant == 'repaired' and row['path'] == 'hydro/hydro_evaluate.h':
                continue
            require(sha(ROOT/variant/row['path']) == row['sha256'], 'Unexpected isolated source diff')
    configs = {}
    for variant, method in [('reference','mfv'),('repaired','mfv'),('mfm_probe','mfm')]:
        cfg = ROOT/variant/'Config.sh'
        require(sha(cfg) == sha(STUDY/('Config_'+method+'.sh')), 'Config changed')
        configs[variant] = sha(cfg)
    report = dict(status='isolated_build_and_source_checks_only',
                  script_sha256=sha(__file__), manifest_sha256=sha(ROOT/'source_manifest.json'),
                  config_sha256=configs, native_simulations_started=0, commands={}, binaries={})
    report['source_diff'] = ''.join(difflib.unified_diff(reference.splitlines(True),
        repaired.splitlines(True), fromfile='reference/hydro/hydro_evaluate.h',
        tofile='repaired/hydro/hydro_evaluate.h'))
    report['toolchain'] = {name: subprocess.check_output(argv, text=True).strip()
        for name, argv in [('mpicc',['mpicc','--version']),('mpi_wrapper',['mpicc','--showme']),
                           ('make',['make','--version'])]}
    locks = []
    try:
        for name in ['benchmark.lock','production.lock']:
            stream = open('/home/kaan/performance_20260907/'+name, 'a')
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
            locks.append(stream)
        for variant in ['reference','repaired']:
            argv = ['make','-j2','EXEC=GIZMO_'+variant,'HG_COMMIT=a828c4b',
                    'HG_BRANCH=master','HG_REPO=https://github.com/pfhopkins/gizmo-public.git']
            report['commands'][variant] = command(argv, ROOT/variant, ROOT/(variant+'_build.log'))
            binary = ROOT/variant/('GIZMO_'+variant)
            report['binaries'][variant] = dict(path=str(binary), bytes=binary.stat().st_size, sha256=sha(binary))
        report['commands']['mfm_config'] = command(['perl','prepare-config.perl','Config.sh'],
             ROOT/'mfm_probe', ROOT/'mfm_config.log')
        for variant in ['reference','repaired','mfm_probe']:
            tree = ROOT/variant
            report['commands'][variant+'_warnings'] = command(
                ['mpicc',*PROBE_FLAGS,'-S','hydro/hydro_toplevel.c','-o','/dev/null'],
                tree, ROOT/(variant+'_warnings.log'))
            warning = (ROOT/(variant+'_warnings.log')).read_text()
            hit = any('dt_hydrostep_i' in line and 'uninitialized' in line for line in warning.splitlines())
            require(hit == (variant == 'reference'), 'Unexpected target warning status: '+variant)
            report['commands'][variant+'_preprocess'] = command(
                ['mpicc',*PROBE_FLAGS,'-E','-P','hydro/hydro_toplevel.c','-o',str(ROOT/(variant+'.i'))],
                tree, ROOT/(variant+'_preprocess.log'))
        mfm = (ROOT/'mfm_probe.i').read_text()
        start = mfm.index('int hydro_force_evaluate(int target')
        # This occurrence is the native definition, not a prototype.
        body = mfm[start:]
        occurrences = [line.strip() for line in body.splitlines()
                       if 'dt_hydrostep_i' in line or 'dt_hydrostep' in line]
        report['mfm_active_timestep_lines'] = occurrences
        require('double dmass_holder = Fluxes.rho * dt_hydrostep_i' not in body,
                'Unexpected MFV integrated mass in MFM')
        report['mfm_scope'] = 'Active preprocessed lines retained for review; no MFM rebuild/run or universal equivalence claim.'
        for row in manifest['source_files']:
            require(sha(CANON/row['path']) == row['sha256'], 'Canonical source mutated during build')
        report['original_binary_sha256'] = sha(STUDY/'GIZMO_mfv_pair')
        require(report['original_binary_sha256'] == 'b7634f844d98ceef246d66e2243827f0c5774c9997b92bd8ffeedfdf940eed91',
                'Original binary changed')
        with (ROOT/'build_report.json').open('x') as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps({k:report[k] for k in ['status','binaries','native_simulations_started']}))
    finally:
        for stream in reversed(locks):
            stream.close()


if __name__ == '__main__':
    main()
