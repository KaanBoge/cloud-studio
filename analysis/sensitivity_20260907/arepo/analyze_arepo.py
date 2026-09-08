"""Within-Arepo scalar curves; native Voronoi outputs, not lattice densities."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_arepo import ROOT,sha,save,pair_initial
from verify_yt_smokes import check as yt_check

def delta(a,b):
    grid=np.linspace(0,5,101);curves=[]
    for s in (a,b):
        t=np.array([r['t_over_tcc'] for r in s]);m=np.array([r['dense_mass_over_initial'] for r in s])
        if not np.all(np.isfinite(t)) or not np.all(np.isfinite(m)) or t[0]!=0 or t[-1]<5-1e-10 or not np.all(np.diff(t)>0):raise ValueError('Incomplete/invalid time series')
        curves.append(np.interp(grid,t,m))
    return float(np.max(abs(curves[0]-curves[1])))

def main():
    batch=json.loads((ROOT/'batch.json').read_text())
    if batch['status'] not in ('held_storage','held_further_validation','complete_native_checks'):raise ValueError('Worker not safely finished')
    cases={(r['level'],r['mode']):r for r in batch['finished']}
    if set(cases)!={(l,m) for l in (3,4) for m in (0,1)}:raise ValueError('Four completed controls required')
    dest=ROOT/'analysis';dest.mkdir(exist_ok=False);pairs=[];series={}
    for level in (3,4):
        a,b=[cases[level,m] for m in (0,1)];initial=pair_initial(a,b);errors=[]
        for case in (a,b):
            folder=Path(case['directory'])
            if sha(folder/'param.txt')!=case['native_input_sha256'] or sha(folder/'IC.hdf5')!=case['ic_sha256']:raise ValueError('Run input changed')
            for row in case['series']:errors.extend(yt_check(row,case['physics']).values())
            series[folder.name]=case['series']
        if a['series'][0]['dense_mass']!=b['series'][0]['dense_mass'] or a['series'][0]['tracer_mass']!=b['series'][0]['tracer_mass']:raise ValueError('Initial denominator differs')
        pairs.append(dict(initial_lattice_level=level,frames_per_variant=[a['unique_snapshots'],b['unique_snapshots']],initial_checks=initial,
            peak_curve_difference_over_initial_mass=delta(a['series'],b['series']),independent_max_relative_mass_error=max(errors),
            native_initial_deviations=[c['series'][0]['native_initial_check'] for c in (a,b)],
            final_dense_fractions=[c['series'][-1]['dense_mass_over_initial'] for c in (a,b)],
            final_inbox_tracer_fractions=[c['series'][-1]['tracer_mass_over_initial'] for c in (a,b)],
            final_actual_t_over_tcc=[c['series'][-1]['t_over_tcc'] for c in (a,b)],wall_seconds=[c['wall_seconds'] for c in (a,b)],
            peak_child_rss_gib=max(c['peak_child_rss_gib'] for c in (a,b))))
    p=cases[3,0]['physics']
    report=dict(status='share_with_caveats',code='Arepo',chi=p['chi'],mach=p['mach'],pairs=pairs,series=series,
        batch_sha256=sha(ROOT/'batch.json'),analysis_sha256=sha(__file__),
        methodology='Native density threshold rho>rho_cloud_initial/3, fixed native initial mass denominator. Native times plotted. Scalar peak difference interpolated to 0:0.05:5 t_cc. Independent yt Arepo native particle sums with explicit rectangular bounds.',
        caveats=['Periodic streamwise boundary retained, not matched to grid-code inflow/outflow. Tracer can recirculate; in-box mass is not proof it never crossed a boundary.',
            'Original jittered lattice gives native Voronoi density and pressure perturbations; report their measured magnitude. These are identical within each initial pair.',
            'Initial lattice level is not a fixed later moving-mesh resolution. Coarse tests do not certify convergence or a universal reuse decision.',
            'All native snapshots, restart files and failed smoke attempts retained. No cooling or frame tracking enabled.'])
    save(dest/'report.json',report)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for l,color in ((3,'#0072B2'),(4,'#D55E00')):
        for m,style,label in ((0,'-','sharp'),(1,'--','historical')):
            s=cases[l,m]['series'];t=[r['t_over_tcc'] for r in s]
            for ax,key in zip(axes,('dense_mass_over_initial','tracer_mass_over_initial')):
                ax.plot(t,[r[key] for r in s],color=color,ls=style,label=f'initial L{l} {label}')
    for ax,label in zip(axes,('Dense mass / initial dense mass','In-box tracer mass / initial tracer mass')):
        ax.set(xlabel=r'$t/t_{cc}$',ylabel=label,xlim=(0,5.02));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Arepo velocity sensitivity | chi=100, Mach 2\nPeriodic x; original jittered-mesh pressure perturbations retained')
    fig.savefig(dest/'mass_and_retention.png',dpi=180);plt.close(fig);print(json.dumps(pairs,indent=2))

if __name__=='__main__':main()
