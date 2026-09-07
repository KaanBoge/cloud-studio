"""Flash-X full-state mass curves with independent yt leaf-cell sums. No tracer."""
import gc
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yt
from run_flashx import ROOT,sha,save,pair_initial,parameters
yt.set_log_level(40)

def independent(row,p):
    ds=yt.load(row['snapshot']);ad=ds.all_data()
    rho=ad['flash','dens'].to_value('code_density');dv=ad['index','cell_volume'].to_value('code_length**3')
    mass=rho*dv
    if len(rho)!=row['cells'] or abs(float(ds.current_time.to_value('code_time'))-row['time_code'])>1e-12:raise ValueError('yt native time/cell mismatch')
    direct=dict(dense_mass=float(mass[rho>p['rho_wind']*p['chi']/3].sum()),total_mass=float(mass.sum()))
    error=max(abs(value-row[key])/max(abs(row[key]),1e-12) for key,value in direct.items())
    if error>1e-11:raise ValueError('yt mass disagrees with native HDF5 leaf sum')
    del ad,ds;gc.collect();return error

def curve_delta(a,b):
    for series in (a,b):
        t=np.array([r['t_over_tcc'] for r in series]);m=np.array([r['dense_mass_over_initial'] for r in series])
        if not np.all(np.isfinite(t)) or not np.all(np.isfinite(m)) or not np.all(np.diff(t)>0) or t[0]!=0 or t[-1]<5-1e-10:
            raise ValueError('Invalid time coverage for curve comparison')
    grid=np.linspace(0,5,101)
    curves=[np.interp(grid,[r['t_over_tcc'] for r in s],[r['dense_mass_over_initial'] for r in s]) for s in (a,b)]
    return float(np.max(abs(curves[0]-curves[1])))

def main():
    batch=json.loads((ROOT/'batch.json').read_text())
    if batch['status'] not in ('held_storage','complete_native_checks'):raise ValueError('Worker unfinished or needs review')
    cases={(r['level'],r['mode']):r for r in batch['finished']}
    if set(cases)!={(l,m) for l in (3,4) for m in (0,1)}:raise ValueError('Unexpected completed scope')
    dest=ROOT/'analysis';dest.mkdir(exist_ok=False);pairs=[];series={}
    for level in (3,4):
        a,b=[cases[level,m] for m in (0,1)];checks=pair_initial(a,b);errors=[]
        for case in (a,b):
            source=Path(case['directory'])/'flash.par'
            if sha(source)!=case['input_sha256']:raise ValueError('Input changed')
            p=parameters(source);errors.append(max(independent(row,p) for row in case['series']))
            series[Path(case['directory']).name]=case['series']
        if a['series'][0]['dense_mass']!=b['series'][0]['dense_mass']:raise ValueError('Initial denominator differs')
        pairs.append(dict(level=level,frames_per_variant=[a['unique_snapshots'],b['unique_snapshots']],initial_checks=checks,
            max_abs_curve_delta_over_initial_mass=curve_delta(a['series'],b['series']),
            final_dense_fractions=[r['series'][-1]['dense_mass_over_initial'] for r in (a,b)],
            final_actual_t_over_tcc=[r['series'][-1]['t_over_tcc'] for r in (a,b)],
            independent_max_relative_mass_error=max(errors),wall_seconds=[r['wall_seconds'] for r in (a,b)],
            sampled_peak_solver_child_rss_gib=max(r['peak_child_rss_gib'] for r in (a,b)),tracer_retention=None))
    report=dict(status='share_with_caveats',code='Flash-X',chi=100,mach=2,pairs=pairs,series=series,
        source_batch_sha256=sha(ROOT/'batch.json'),analysis_sha256=sha(__file__),
        methodology='Full float64 checkpoint leaf-cell sums checked independently with yt. Density threshold rho>rho_cloud_initial/3 and fixed measured initial denominator. Plot native times. Only scalar difference interpolates to 0:0.05:5 t_cc.',
        caveats=['No passive tracer in the native Flash-X recipe; no tracer-based material retention claim.',
            'Full checkpoints now saved at every plot time, without checkpoint overwriting; all original plotfields/precision retained.',
            'L3/L4 are coarse controls, not convergence or a universal historical reuse decision.',
            'All actual native times retained. Extra same-time forced outputs remain in the raw directory and are listed separately.'])
    save(dest/'report.json',report)
    fig,ax=plt.subplots(figsize=(8,4.7),layout='constrained')
    for level,color in ((3,'#0072B2'),(4,'#D55E00')):
        for mode,style,name in ((0,'-','sharp'),(1,'--','historical')):
            s=cases[level,mode]['series'];ax.plot([r['t_over_tcc'] for r in s],[r['dense_mass_over_initial'] for r in s],color=color,ls=style,label=f'L{level} {name}')
    ax.set(title='Flash-X velocity sensitivity | chi=100, Mach 2\nFull-state native outputs; no passive tracer',xlabel=r'$t/t_{cc}$',ylabel=r'$M_{dense}(t)/M_{dense}(0)$',xlim=(0,5.02),ylim=(0,1.1))
    ax.grid(alpha=.2);ax.legend();fig.savefig(dest/'mass_evolution.png',dpi=180);plt.close(fig)
    print(json.dumps(pairs,indent=2),flush=True)

if __name__=='__main__':main()
