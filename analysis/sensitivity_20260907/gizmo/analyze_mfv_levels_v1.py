"""Compare accepted repaired MFV L3/L4 mass curves without rerunning solvers.

Reuses the pinned accepted L3 scalar report and new independently checked L4
series. Verifies new raw bytes and frozen provenance, not a repeated field/yt
extraction. Native-time curves are preserved; only scalar peaks interpolate.
Run with /home/kaan/venv/bin/python under WSL. Output is create-once.
"""
import fcntl
import hashlib
import json
import math
import shutil
import statistics
import unittest
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import psutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DEST = HERE / 'mfv_analysis_levels_v1'
RAW = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/mfv_L4_velocity_pair_v1')
FROZEN = Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_full_runner_v1')
PREP = FROZEN.parent / 'l4_prepare_runner_v1'
PLAN_SHA = '2b77bb64257e2826dfe241ca6fb31eedcd5b868d73eeb4761cf96ac079430d7c'
L3_SHA = 'db45f9d985a4e8eb87b63f0247d1d5f61572acfaab5dad6f9272dfe36b0a017d'
BINARY_SHA = '4784336422c25db4714c6f56ef95337347f4be18dfd622e2b7e9acf7e1fe3d3c'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, obj):
    with Path(path).open('x') as handle:
        json.dump(obj, handle, indent=2, allow_nan=False)
        handle.write('\n')


def curve(rows, tcc):
    require(math.isfinite(tcc) and tcc > 0 and len(rows) >= 2, 'Missing scalar series or time unit')
    t = np.array([r['time_code']/tcc for r in rows], dtype=float)
    m = np.array([r['dense_mass'] for r in rows], dtype=float)
    require(np.isfinite(t).all() and np.isfinite(m).all(), 'Nonfinite scalar')
    require(t[0] == 0 and abs(t[-1]-5) <= 1e-12 and (np.diff(t) > 0).all(), 'Incomplete, duplicate or disordered times')
    require(m[0] > 0 and (m >= 0).all(), 'Invalid dense mass')
    return t, m


def scalar_interp(t, y, x):
    """Independent scalar interpolation with no extrapolation/clamping."""
    require(t[0] <= x <= t[-1], 'Interpolation outside native time support')
    if x == t[-1]:
        return y[-1]
    right = bisect_right(t, x)
    weight = (x-t[right-1])/(t[right]-t[right-1])
    return (1-weight)*y[right-1]+weight*y[right]


def metrics(a, b, tcc):
    ta, ma = curve(a, tcc)
    tb, mb = curve(b, tcc)
    require(ma[0] == mb[0], 'Different within-pair initial dense mass')
    denominator = float(ma[0])
    grid = np.linspace(0, 5, 101)
    ca, cb = np.interp(grid, ta, ma/denominator), np.interp(grid, tb, mb/denominator)
    delta = np.abs(ca-cb)
    separate = np.array([abs(scalar_interp(ta.tolist(), (ma/denominator).tolist(), x)-
                            scalar_interp(tb.tolist(), (mb/denominator).tolist(), x)) for x in grid])
    error = float(np.max(abs(delta-separate)))
    require(error <= 8*np.finfo(float).eps, 'Independent scalar calculation differs')
    i = int(np.argmax(delta))
    return dict(initial_dense_mass=denominator,
        peak_curve_difference_over_initial_mass=float(delta[i]), first_peak_grid_time=float(grid[i]),
        final_dense_fractions=[float(ma[-1]/denominator), float(mb[-1]/denominator)],
        grid_times=grid.tolist(), difference_over_initial_mass=delta.tolist(),
        independent_scalar_max_absolute_difference=error)


def validate_l4(cases, physics):
    require(len(cases) == 2 and [c['law'] for c in cases] == ['sharp13', 'tanh13'], 'Missing/reordered laws')
    require(cases[0]['input_sha256'] == cases[1]['input_sha256'], 'Different full parameters')
    require(physics['chi'] == 100 and physics['mach'] == 2 and physics['ranks'] == 8, 'Wrong study scope')
    for case in cases:
        require(case['status'] == 'passed_full_native_checks' and case['physics'] == physics
                and case['binary_sha256'] == BINARY_SHA, 'Unaccepted case or changed physical/native recipe')
        r = case['resources']
        require(r['returncode'] == 0 and r['error'] is None and r['wall_seconds'] > 0, 'Solver did not finish normally')
        rows, cadence = case['rows'], case['cadence']
        curve(rows, physics['t_cc'])
        require(cadence['bits'] == 60 and cadence['actual_count'] == cadence['expected_count'] == len(rows)
                and 0 <= cadence['maximum_offset'] <= cadence['tolerance_code'], 'Missing native cadence evidence')
        require(len({row['path'] for row in rows}) == len(rows), 'Duplicate snapshot path')
        for row in rows:
            require(row['elements'] == 524288 and row['time_code']/physics['t_cc'] == row['t_over_tcc'], 'Wrong resolution or time')
            require(math.isfinite(row['total_mass']) and 0 <= row['dense_mass'] <= row['total_mass'], 'Invalid mass bounds')
            require(math.isfinite(row['min_energy']) and row['min_energy'] > 0, 'Nonpositive/nonfinite stored energy')
            errors = row['independent_relative_errors']
            require(len(errors) == 2 and all(math.isfinite(e) and 0 <= e <= 1e-11 for e in errors), 'Independent reader failure')
        mass = case['terminal']['mass_account']
        require(mass['passes'] and mass['response_detected'] and abs(mass['residual']) <= mass['allowance'], 'Terminal mass gate failed')
    return metrics(cases[0]['rows'], cases[1]['rows'], physics['t_cc'])


def verify_file(row):
    path = Path(row['path'])
    require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Changed retained raw: '+str(path))
    return 1


def main():
    require(not DEST.exists(), 'Existing analysis is immutable')
    held = []
    for name in ('benchmark.lock', 'production.lock'):
        handle = open('/home/kaan/performance_20260907/'+name, 'rb')
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held.append(handle)
    blocked = {'GIZMO_repaired', 'GIZMO', 'Gadget4', 'Gadget4_3d_mixed_hfix', 'athena', 'athena_l6',
               'athenaPK', 'flash4', 'flashx', 'enzo.exe', 'ramses3d', 'gasoline', 'make'}
    require(not any(p.info['name'] in blocked for p in psutil.process_iter(['name'])), 'Competing solver/build')
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_mfv_levels_v1.py')
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    require(tests.wasSuccessful() and tests.testsRun == 14, 'New scalar/metadata tests failed or missing')
    old_path = HERE/'mfv_repaired_pair.json'
    require(sha(old_path) == L3_SHA, 'Accepted L3 source changed')
    old = read(old_path)
    require(old['status'] == 'passed_repaired_mfv_L3_pair' and old['binary_sha256'] == BINARY_SHA, 'Wrong accepted L3 source')
    require(sha(FROZEN/'plan.json') == PLAN_SHA, 'Frozen full plan changed')
    plan, prep = read(FROZEN/'plan.json'), read(PREP/'plan.json')
    pins = dict(plan['pins'])
    for path, digest in prep['pins'].items():
        require(path not in pins or pins[path] == digest, 'Inconsistent frozen pin')
        pins[path] = digest
    for path, digest in pins.items():
        require(sha(path) == digest, 'Frozen source/input changed: '+path)
    batch = read(RAW/'batch.json')
    require(batch['status'] == 'passed_full_pair_pending_analysis' and batch['new_full_controls_validated'] == 2
            and batch['plan_sha256'] == PLAN_SHA, 'New pair not ready for analysis')
    require(old['physics'] == plan['physics'], 'Physical metadata changed between resolutions')
    l4 = validate_l4(batch['finished'], plan['physics'])
    l3 = metrics(old['sharp_outputs'], old['historical_outputs'], old['physics']['t_cc'])
    previous = old['mass_comparison']
    require(l3['initial_dense_mass'] == previous['initial_dense_mass'] and
            l3['peak_curve_difference_over_initial_mass'] == previous['maximum_absolute_separation_fraction'] and
            l3['first_peak_grid_time'] == previous['time_of_maximum_tcc'], 'Accepted L3 metric drift')
    cases = {'3': [{'law':law, 'rows':old[key], 'resources':old[res]} for law,key,res in
                   [('sharp13','sharp_outputs','sharp_resources'),('tanh13','historical_outputs','historical_resources')]],
             '4': batch['finished']}
    for case, label in zip(cases['3'], ('sharp', 'historical')):
        t, m = curve(case['rows'], old['physics']['t_cc'])
        require(t.tolist() == previous['series'][label]['native_times_tcc'] and
                (m/l3['initial_dense_mass']).tolist() == previous['series'][label]['dense_mass_fraction'], 'Accepted L3 curve drift')
    raw_rows, provenance = [], {}
    for case in cases['4']:
        folder = RAW/case['law']
        require(read(folder/'validation.json') == case and read(folder/'result.json') == case['resources'], 'Native ledgers disagree')
        launch = read(folder/'launch.json')
        require(launch['law'] == case['law'] and launch['plan_sha256'] == PLAN_SHA
                and launch['binary_sha256'] == BINARY_SHA, 'Wrong native launch')
        require(sha(folder/'params.txt') == case['input_sha256'] and sha(folder/'ics.hdf5') == case['ic_sha256'], 'Changed inputs')
        terminal = case['terminal']
        require(len(terminal['files']) == 8, 'Missing terminal rank files')
        retained = {row['path']:row for row in terminal['retained_files']}
        require(all(retained.get(row['path'], {}).get('sha256') == row['sha256'] for row in terminal['files']), 'Terminal retention mismatch')
        for row in case['rows']+list(retained.values()):
            require(Path(row['path']).is_relative_to(folder/'output'), 'Raw outside native case')
            raw_rows.append(row)
        samples = [json.loads(line) for line in (folder/'resources.jsonl').read_text().splitlines()]
        require(max(r['child_rss_bytes'] for r in samples) == case['resources']['peak_child_rss_bytes'], 'RSS ledger differs')
        require(statistics.median(r['busy_cpu_workers'] for r in samples if r['busy_cpu_workers'] is not None) ==
                case['resources']['median_busy_cpu_workers'], 'CPU ledger differs')
        for name in ('validation.json','result.json','launch.json','run.log','resources.jsonl','params.txt','ics.hdf5'):
            provenance[str(folder/name)] = sha(folder/name)
    print('Checking new native snapshot/restart bytes; no native field analysis is repeated.', flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        verified = sum(pool.map(verify_file, raw_rows))
    new_states = sum(len(c['rows']) for c in cases['4'])
    count = sum(len(c['rows']) for group in cases.values() for c in group)
    report = dict(status='share_with_caveats',code='GIZMO MFV, isolated timestep repair',levels=[3,4],controls=4,
        native_states=count,new_controls=2,new_native_states=new_states,reused_accepted_controls=2,
        physics=plan['physics'],binary_sha256=BINARY_SHA,metrics={'3':l3,'4':l4},cases_by_level=cases,
        source_sha256={str(old_path):L3_SHA,str(RAW/'batch.json'):sha(RAW/'batch.json'),str(FROZEN/'plan.json'):PLAN_SHA},
        frozen_source_input_pins=pins,new_case_file_sha256=provenance,analysis_sha256=sha(__file__),
        metric_definition='Density > initial cloud density/3. Fixed measured native initial dense mass per level/pair. All actual times plotted; only scalar peaks interpolate linearly onto 0:0.05:5 tcc. No new or retimed 3D states.',
        caveats=['Two coarse initial lattices: L3 64x32x32,3.2 elements/R; L4 128x64x64,6.4 elements/R. Not convergence or exact-solution error.',
        'Same repaired native MFV executable for both laws/levels. Original failed MFV data is excluded; MFM output trajectories are not used.',
        'Original kernel-derived initial pressure is slightly nonuniform; L4 0.99907852..0.99913334 times nominal. Same within each pair, not universally matched cross-code pressure.',
        'Fully periodic boundaries permit recirculation; particle-ID mass is not a passive material tracer. No all-material-retained claim.',
        'Native evolved velocities are half-kick staggered, not validated as simultaneous with snapshot header time. These are mass diagnostics.',
        'Conserved MassTrue plus pending dMass passes the existing engineering accumulation gate. Snapshot predicted mass alone is not that ledger. This is not a physical-accuracy theorem.',
        'L3 ext4 and L4 Windows C: storage differ; wall times are not a controlled scaling benchmark or a level6 forecast.',
        'All raw data remains saved. Restart-prefix checks/hashes do not certify checkpoint-resume behavior. No cooling, tracking, MHD, other Mach, production viewer entries or blanket replacement enabled.'])
    DEST.mkdir()
    fig, axes = plt.subplots(2,1,figsize=(10,8),layout='constrained',sharex=True,gridspec_kw={'height_ratios':[2,1]})
    for level, group in cases.items():
        color, marker = ('#0072B2','o') if level == '3' else ('#D55E00','s')
        for case in group:
            t,m = curve(case['rows'], plan['physics']['t_cc'])
            axes[0].plot(t,m/report['metrics'][level]['initial_dense_mass'],color=color,marker=marker,markevery=20,ms=3,
                         ls='-' if case['law']=='sharp13' else '--',lw=1.8,
                         label=f"L{level} | {'sharp' if case['law']=='sharp13' else 'historical tanh'}")
        r = report['metrics'][level]
        axes[1].plot(r['grid_times'],100*np.array(r['difference_over_initial_mass']),color=color,marker=marker,markevery=20,ms=3,
                     label=f"L{level}: peak {100*r['peak_curve_difference_over_initial_mass']:.2f}%")
    axes[0].set(title='Repaired native MFV velocity sensitivity | chi = 100, Mach = 2\nTwo coarse resolutions; density selection, not cloud-material retention',
                ylabel='Dense mass / fixed initial dense mass',ylim=(0,None))
    axes[1].set(xlabel=r'$t/t_{cc}$',ylabel='Absolute separation\n(% of initial dense mass)',xlim=(0,5),ylim=(0,None))
    for ax in axes:
        ax.grid(alpha=.18); ax.spines[['top','right']].set_visible(False); ax.legend(fontsize=10,loc='best')
    fig.savefig(DEST/'mass_L3_L4.png',dpi=180);plt.close(fig)
    report['plot_sha256'] = sha(DEST/'mass_L3_L4.png')
    save(DEST/'report.json',report)
    validation = dict(status='passed_report_and_new_raw_provenance_checks',unit_tests_passed=tests.testsRun,
        new_snapshots_byte_verified=new_states,new_restart_files_byte_verified=verified-new_states,
        new_field_reader_checks_reused=new_states,old_scalar_report_reused=True,native_experiments_rerun=0,
        source_pins_checked=len(pins),report_sha256=sha(DEST/'report.json'),test_script_sha256=sha(HERE/'test_mfv_levels_v1.py'),
        independent_scalar_max_absolute_difference=max(l3['independent_scalar_max_absolute_difference'],l4['independent_scalar_max_absolute_difference']))
    save(DEST/'validation.json',validation)
    for source,name in ((RAW/'batch.json','full_l4_batch.json'),(FROZEN/'plan.json','full_l4_plan.json'),(RAW/'windows_readback.json','windows_readback.json')):
        shutil.copy2(source,DEST/name)
    print(json.dumps(dict(status=report['status'],metrics={k:{x:v[x] for x in ('initial_dense_mass','peak_curve_difference_over_initial_mass','first_peak_grid_time','final_dense_fractions')} for k,v in report['metrics'].items()},validation=validation),indent=2),flush=True)


if __name__ == '__main__':
    main()
