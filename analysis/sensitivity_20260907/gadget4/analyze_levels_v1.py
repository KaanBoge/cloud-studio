"""New L3/L4 scalar comparison; reuse accepted L3 analysis, never rerun solvers.

Run under WSL Python. Checks frozen provenance and new L4 raw byte hashes,
but does not repeat the already completed native field/yt analysis.
"""
import hashlib
import json
import math
import shutil
import statistics
import unittest
from bisect import bisect_right
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DEST = HERE / 'analysis_levels_v1'
RAW = Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/gadget4_L4_velocity_pair_v1')
FROZEN = Path('/home/kaan/sensitivity_20260907/gadget4/runner_full_l4_ntfs_v1')
PLAN_SHA = 'a66c291cdaf6858a0c69560a47ed137f5d026e85851af205134b5cb0d67bdba4'


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


def curve(rows):
    require(len(rows) == 101, 'Expected all 101 native states')
    t = np.array([r['t_over_tcc'] for r in rows], dtype=float)
    m = np.array([r['dense_mass'] for r in rows], dtype=float)
    require(np.all(np.isfinite(t)) and np.all(np.isfinite(m)), 'Nonfinite scalar')
    require(t[0] == 0 and abs(t[-1]-5) <= 1e-12 and np.all(np.diff(t)>0), 'Incomplete/duplicate/unordered time')
    require(m[0]>0 and np.all(m>=0), 'Invalid dense mass')
    return t, m


def scalar_interp(t, y, x):
    """Independent pure-Python scalar interpolation, not numpy.interp."""
    if x <= t[0]:
        return y[0]
    if x >= t[-1]:
        return y[-1]
    right = bisect_right(t, x)
    weight = (x-t[right-1])/(t[right]-t[right-1])
    return (1-weight)*y[right-1]+weight*y[right]


def metrics(a, b):
    ta, ma = curve(a)
    tb, mb = curve(b)
    require(ma[0] == mb[0], 'Pair must use equal fixed initial dense mass')
    denominator = float(ma[0])
    grid = np.linspace(0,5,101)
    ca, cb = np.interp(grid,ta,ma/denominator), np.interp(grid,tb,mb/denominator)
    delta = np.abs(ca-cb)
    independent = np.array([abs(scalar_interp(ta.tolist(), (ma/denominator).tolist(), x)-
                               scalar_interp(tb.tolist(), (mb/denominator).tolist(), x)) for x in grid])
    error = float(np.max(abs(delta-independent)))
    require(error <= 8*np.finfo(float).eps, 'Independent scalar comparison differs')
    i = int(np.argmax(delta))
    return dict(initial_dense_mass=denominator,
                peak_curve_difference_over_initial_mass=float(delta[i]),
                first_peak_grid_time=float(grid[i]),
                final_dense_fractions=[float(ma[-1]/denominator),float(mb[-1]/denominator)],
                grid_times=grid.tolist(), difference_over_initial_mass=delta.tolist(),
                independent_scalar_max_absolute_difference=error)


def validate_pair(cases, level):
    require(len(cases)==2 and [c['mode'] for c in cases]==[0,1], 'Missing or reordered velocity laws')
    a,b = cases
    require(a['physics']==b['physics'] and a['input_sha256']==b['input_sha256']
            and a['binary_sha256']==b['binary_sha256'], 'Paired physics, parameters or binary differ')
    p = a['physics']
    require(p['chi']==100 and p['mach']==2 and p['ranks']==8, 'Unexpected experiment scope')
    for case in cases:
        require(case['status']=='complete_independent_checks' and case['returncode']==0, 'Unaccepted native case')
        curve(case['series'])
        for row in case['series']:
            require(row['elements']==2**(3*level+7), 'Wrong native resolution')
            require(abs(row['time_code']/p['t_cc']-row['t_over_tcc'])<=1e-14, 'Wrong normalized time')
            require(set(row['independent_relative_errors'])=={'total_mass','dense_mass','tagged_mass'}, 'Missing independent mass checks')
            require(all(math.isfinite(x) and 0<=x<=1e-11 for x in row['independent_relative_errors'].values()), 'Independent field-reader failure')
            require(all(math.isfinite(row[x]) and row[x]>=0 for x in ('total_mass','dense_mass','tagged_mass')), 'Invalid mass')
    return metrics(a['series'],b['series'])


def main():
    require(not DEST.exists(), 'Existing analysis is immutable')
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_levels_v1.py')
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    require(tests.wasSuccessful() and tests.testsRun==12, 'New analysis tests failed or missing')
    old_path = HERE/'l3_report.json'
    repo_old = Path('/mnt/c/Users/kaanb/cloud-studio-repo/analysis/sensitivity_20260907/gadget4/l3_report.json')
    require(sha(old_path)==sha(repo_old), 'Accepted L3 source differs from published repository')
    old = read(old_path)
    require(old['status']=='share_with_caveats' and old['controls']==2 and old['native_states']==202, 'Unexpected accepted L3 report')
    batch = read(RAW/'batch.json')
    require(batch['status']=='complete_independent_pair_checks' and batch['new_full_controls']==2
            and batch['plan_sha256']==PLAN_SHA, 'New native pair incomplete or wrong frozen plan')
    require(sha(FROZEN/'plan.json')==PLAN_SHA, 'Frozen plan changed')
    plan = read(FROZEN/'plan.json')
    for path,digest in plan['pins'].items():
        require(sha(path)==digest, 'Frozen native dependency/input changed: '+path)
    levels = {3: old['cases'], 4: batch['finished']}
    metrics_by_level = {str(level):validate_pair(cases,level) for level,cases in levels.items()}
    for field in ('initial_dense_mass','peak_curve_difference_over_initial_mass','first_peak_grid_time','final_dense_fractions'):
        require(metrics_by_level['3'][field]==old['metrics'][field], 'Accepted L3 scalar metric drift')
    require(levels[3][0]['physics']==levels[4][0]['physics'], 'Cross-resolution physical metadata changed')
    provenance = {}
    verified = 0
    for case in levels[4]:
        folder = Path(case['directory'])
        require(folder==RAW/('tanh13' if case['mode'] else 'sharp13'), 'Unexpected new raw path')
        require(read(folder/'result.json')==case, 'Case and batch ledgers differ')
        require(case['cadence']['native_count']==101 and case['cadence']['max_exact_scheduler_error']==0
                and case['cadence']['actual_times']==[r['time_code'] for r in case['series']], 'Native cadence evidence differs')
        require(sha(folder/'params.txt')==case['input_sha256'] and sha(folder/'ics.hdf5')==case['ic_sha256'], 'Native inputs changed')
        for row in case['series']+case['retained_restarts']:
            path = Path(row.get('snapshot',row.get('path')))
            require(path.is_relative_to(folder/'output') and path.stat().st_size==row['bytes'] and sha(path)==row['sha256'], 'Retained raw bytes changed')
            verified += 1
        samples = [json.loads(line) for line in (folder/'resources.jsonl').read_text().splitlines()]
        require(max(r['rss_bytes'] for r in samples)/1024**3==case['peak_child_rss_gib'], 'RSS ledger mismatch')
        # The sampler had no children at its first sample. Its second sample
        # establishes CPU counters; neither startup row enters runner.busy.
        require(samples[0]['rss_bytes']==0 and all(r['rss_bytes']>0 for r in samples[1:])
                and samples[0]['busy_cpu_cores']==samples[1]['busy_cpu_cores']==0,
                'Unexpected resource sampler startup; review CPU provenance')
        require(statistics.median(r['busy_cpu_cores'] for r in samples[2:])==case['median_busy_cpu_workers'], 'CPU ledger mismatch')
        for name in ('result.json','run.log','resources.jsonl','params.txt','ics.hdf5'):
            provenance[str(folder/name)] = sha(folder/name)
    require(verified==218, 'Missing snapshot or restart hashes')
    sources = {str(old_path):sha(old_path),str(RAW/'batch.json'):sha(RAW/'batch.json'),str(FROZEN/'plan.json'):PLAN_SHA}
    report = dict(status='share_with_caveats',code='Gadget-4 SPH',levels=[3,4],controls=4,native_states=404,
        new_controls=2,new_native_states=202,reused_accepted_controls=2,
        source_sha256=sources,new_case_file_sha256=provenance,analysis_sha256=sha(__file__),
        metrics=metrics_by_level,cases_by_level={str(k):v for k,v in levels.items()},
        metric_definition='rho > rho_cloud_initial/3; fixed measured native initial dense mass per resolution pair. Plot all actual native times. Only scalar peak uses declared 0:.05:5 tcc linear interpolation. No frame/time rewriting.',
        caveats=['Two coarse levels (L3 64x32x32,3.2 elements/R; L4 128x64x64,6.4 elements/R). Not demonstrated convergence, exact-solution error or a universal reuse criterion.',
        'Existing Gadget4_3d_mixed_hfix native SPH executable; mean-mass/shortest-box initial smoothing-length seed patch retained in both laws, not pristine upstream.',
        'Native initial SPH pressure is nonuniform: L3 peak3.900326 times nominal; L4 range0.808274..2.104201. Identical within each pair, not a matched uniform-pressure grid baseline.',
        'Fully periodic boundaries permit recirculation. ID-tagged in-box mass cannot demonstrate no boundary crossing and tags only initial r<=R, not the entire tanh tail.',
        'Initial velocity synchronization checked; evolved velocity at native header time remains unvalidated. These are evolved mass diagnostics.',
        'L3 raw was stored on ext4; L4 raw directly on Windows C:. Runtime ratios are not a controlled resolution-scaling benchmark.',
        'No raw data removed. Retained restart byte checks are not a checkpoint-resume validation. No cooling, MHD, other Mach, Galilean tracking, production viewer entry or blanket replacement enabled.'])
    DEST.mkdir()
    fig,axes=plt.subplots(2,1,figsize=(9,8),layout='constrained',gridspec_kw={'height_ratios':[2,1]},sharex=True)
    for level,cases in levels.items():
        for case in cases:
            t,m=curve(case['series'])
            axes[0].plot(t,m/metrics_by_level[str(level)]['initial_dense_mass'],color='#0072B2' if level==3 else '#D55E00',
                ls='-' if case['mode']==0 else '--',lw=1.8,marker='o' if level==3 else 's',markevery=20,ms=3,
                label=f"L{level} | {'sharp' if case['mode']==0 else 'historical tanh'}")
        r=metrics_by_level[str(level)]
        axes[1].plot(r['grid_times'],100*np.array(r['difference_over_initial_mass']),color='#0072B2' if level==3 else '#D55E00',
            marker='o' if level==3 else 's',markevery=20,ms=3,lw=1.8,label=f"L{level}: peak {100*r['peak_curve_difference_over_initial_mass']:.2f}%")
    axes[0].set(title='Gadget-4 velocity sensitivity | chi = 100, Mach = 2\nTwo coarse resolutions; native SPH pressure and periodic boundaries retained',ylabel='Dense mass / fixed initial dense mass',ylim=(0,1.05))
    axes[1].set(xlabel=r'$t/t_{cc}$',ylabel='Absolute separation\n(% of initial dense mass)',xlim=(0,5),ylim=(0,None))
    for ax in axes:
        ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False);ax.legend(fontsize=9,loc='lower left' if ax==axes[0] else 'upper right')
    fig.savefig(DEST/'mass_L3_L4.png',dpi=180);plt.close(fig)
    report['plot_sha256']=sha(DEST/'mass_L3_L4.png')
    save(DEST/'report.json',report)
    validation=dict(status='passed_report_and_new_raw_provenance_checks',unit_tests_passed=tests.testsRun,
        new_snapshots_byte_verified=202,new_restart_files_byte_verified=16,new_field_reader_checks_reused=202,
        old_scalar_report_reused=True,native_experiments_rerun=0,source_pins_checked=len(plan['pins']),
        independent_scalar_max_absolute_difference=max(r['independent_scalar_max_absolute_difference'] for r in metrics_by_level.values()),
        report_sha256=sha(DEST/'report.json'),test_script_sha256=sha(HERE/'test_levels_v1.py'))
    save(DEST/'validation.json',validation)
    for source,name in ((RAW/'batch.json','full_l4_batch.json'),(FROZEN/'plan.json','full_l4_plan.json'),(RAW/'windows_readback.json','windows_readback.json')):
        shutil.copy2(source,DEST/name)
    print(json.dumps(dict(status=report['status'],metrics={k:{x:r[x] for x in ('initial_dense_mass','peak_curve_difference_over_initial_mass','first_peak_grid_time','final_dense_fractions')} for k,r in metrics_by_level.items()},validation=validation),indent=2),flush=True)


if __name__=='__main__':
    main()
