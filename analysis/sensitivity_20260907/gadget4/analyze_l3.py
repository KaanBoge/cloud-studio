"""L3-only native Gadget-4 sensitivity analysis; all raw and actual times retained."""
import fcntl,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4/runner_l3_v2')
from run_full_l3_v2 import ROOT,sha,save,parameters,native_summary,dependencies,cadence

def metric(a,b):
    denominator=a[0]['dense_mass']
    if denominator<=0 or denominator!=b[0]['dense_mass']:raise ValueError('Initial denominator must be fixed and equal within pair')
    curves=[]
    for rows in (a,b):
        times=np.array([r['t_over_tcc'] for r in rows]);mass=np.array([r['dense_mass'] for r in rows])/denominator
        if not np.all(np.isfinite(times)) or not np.all(np.isfinite(mass)) or np.any(np.diff(times)<=0) or times[0]!=0 or abs(times[-1]-5)>1e-12:raise ValueError('Incomplete or invalid actual-time curve')
        curves.append(np.interp(np.linspace(0,5,101),times,mass))
    delta=np.abs(curves[0]-curves[1]);i=int(np.argmax(delta))
    return dict(initial_dense_mass=denominator,peak_curve_difference_over_initial_mass=float(delta[i]),first_peak_grid_time=float(np.linspace(0,5,101)[i]),
        final_dense_fractions=[rows[-1]['dense_mass']/denominator for rows in (a,b)])

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    dependencies();dest=ROOT/'analysis_l3_v1'
    if dest.exists():raise ValueError('Existing analysis must not be overwritten')
    source=ROOT/'full_l3_continuation_v2/batch.json';batch=json.loads(source.read_text());cases=batch['finished']
    if batch['status']!='complete_independent_checks' or [c['mode'] for c in cases]!=[0,1] or any(c['status']!='complete_independent_checks' for c in cases):raise ValueError('Full native pair incomplete')
    if cases[0]['physics']!=cases[1]['physics'] or cases[0]['input_sha256']!=cases[1]['input_sha256']:raise ValueError('Paired native settings mismatch')
    largest=0
    for case in cases:
        folder=Path(case['directory']);values=parameters((folder/'params.txt').read_text())
        if sha(folder/'params.txt')!=case['input_sha256'] or sha(folder/'ics.hdf5')!=case['ic_sha256'] or sha(ROOT/'Gadget4_pair')!=case['binary_sha256']:raise ValueError('Native input/binary hash mismatch')
        cadence([r['time_code'] for r in case['series']],case['physics'],values)
        for row in case['series']:
            path=Path(row['snapshot'])
            if sha(path)!=row['sha256']:raise ValueError('Native output changed')
            a,current=native_summary(path,case['physics'])
            if current['time_code']!=row['time_code'] or current['elements']!=row['elements']:raise ValueError('Native time/count mismatch')
            for field in ('total_mass','dense_mass','tagged_mass'):
                error=abs(current[field]-row[field])/max(abs(row[field]),1e-12);largest=max(largest,error)
                if error>1e-12:raise ValueError('Native mass recheck differs')
            if max(row['independent_relative_errors'].values())>1e-11 or row['dense_mass_over_initial']!=row['dense_mass']/case['series'][0]['dense_mass']:raise ValueError('Independent evidence or normalization differs')
        samples=[json.loads(line) for line in (folder/'resources.jsonl').read_text().splitlines()]
        case['median_busy_cpu_workers']=float(np.median([r['busy_cpu_cores'] for r in samples if r['elapsed_seconds']>=4]))
    result=metric(cases[0]['series'],cases[1]['series']);dest.mkdir()
    fig,ax=plt.subplots(figsize=(8.5,5.2),layout='constrained')
    for case in cases:
        ax.plot([r['t_over_tcc'] for r in case['series']],[r['dense_mass_over_initial'] for r in case['series']],
            color='#0072B2' if case['mode']==0 else '#D55E00',ls='-' if case['mode']==0 else '--',lw=2,label='Sharp' if case['mode']==0 else 'Historical tanh')
    ax.set(title='Native Gadget-4 SPH | L3, chi=100, Mach 2\nSingle coarse resolution; existing periodic / nonuniform-pressure IC',
        xlabel=r'$t/t_{cc}$',ylabel='Dense mass / fixed initial dense mass',xlim=(0,5),ylim=(0,1.05))
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.2);ax.legend(loc='lower left')
    fig.savefig(dest/'mass_L3.png',dpi=180);plt.close(fig)
    report=dict(status='share_with_caveats',code='Gadget-4 SPH',level=3,controls=2,native_states=sum(len(c['series']) for c in cases),
        cases=cases,metrics=result,direct_mass_recheck_max_relative_error=largest,batch_sha256=sha(source),analysis_sha256=sha(__file__),plot_sha256=sha(dest/'mass_L3.png'),
        metric_definition='rho > rho_cloud_initial/3. Fixed measured initial dense mass within pair. Plot uses every actual native time. Scalar peak is linearly interpolated onto0:.05:5tcc; no native frame interpolation.',
        caveats=['Single coarse L3 (3.2elements/R), not resolution convergence, exact-solution error or a universal reuse decision.',
            'Original periodic boundaries and SPH initial pressure up to3.9003x nominal retained identically in both controls; not a matched grid baseline.',
            'Existing hfix smoothing-length seed patch retained, not a pristine upstream binary. No numerics or native data changed.',
            'Native scheduled outputs round earlier or later; exact native scheduler reproduced, not timestamps rewritten.',
            'ID-tagged in-box mass does not demonstrate no periodic boundary crossing. Evolved velocity-time diagnostics remain unvalidated.'])
    save(dest/'report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))

if __name__=='__main__':main()
