"""Measured native MFM L3 sensitivity only; failed MFV is explicitly excluded."""
import json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1')
from run_full_l3 import ROOT,sha,save,check_times

def main():
    batch=json.loads((ROOT/'full_l3_batch.json').read_text())
    cases=sorted([c for c in batch['finished'] if c['variant']=='mfm'],key=lambda c:c['mode'])
    if [c['mode'] for c in cases]!=[0,1] or any(c['status']!='complete_independent_checks' or c['level']!=3 for c in cases):
        raise ValueError('Both complete native MFM L3 controls are required')
    dest=ROOT/'analysis_mfm_l3';dest.mkdir(exist_ok=False)
    for c in cases:
        folder=Path(c['directory'])
        if sha(folder/'params.txt')!=c['input_sha256'] or sha(folder/'ics.hdf5')!=c['ic_sha256']:raise ValueError('Input provenance changed')
        check_times([r['time_code'] for r in c['series']],c['physics'])
        for r in c['series']:
            if sha(r['snapshot'])!=r['sha256'] or max(r['independent_relative_errors'].values())>1e-11:raise ValueError('Native data changed or independent check failed')
    if cases[0]['series'][0]['dense_mass']!=cases[1]['series'][0]['dense_mass']:raise ValueError('Initial denominators differ')
    grid=np.linspace(0,5,101)
    curves=[np.interp(grid,[r['t_over_tcc'] for r in c['series']],[r['dense_mass_over_initial'] for r in c['series']]) for c in cases]
    peak=float(np.max(abs(curves[0]-curves[1])))
    report=dict(status='share_with_caveats',code='GIZMO MFM',level=3,chi=cases[0]['physics']['chi'],mach=cases[0]['physics']['mach'],
        controls=2,frames_per_variant=[len(c['series']) for c in cases],peak_curve_difference_over_initial_mass=peak,
        final_dense_fractions=[c['series'][-1]['dense_mass_over_initial'] for c in cases],
        independent_max_relative_mass_error=max(c['independent_max_relative_mass_error'] for c in cases),
        wall_seconds=[c['wall_seconds'] for c in cases],peak_child_rss_gib=max(c['peak_child_rss_gib'] for c in cases),
        series={str(c['mode']):c['series'] for c in cases},batch_sha256=sha(ROOT/'full_l3_batch.json'),analysis_sha256=sha(__file__),
        scope='MFM L3 historical versus sharp only. MFV failed positivity validation and is not pooled into this result.',
        caveats=['Single coarse level, 3.2 initial elements/R, not a resolution-convergence Figure 2 or universal reuse decision.',
            'Original fully periodic boundaries and native kernel density/pressure deviations retained; not a matched grid inflow/outflow baseline.',
            'No passive material tracer. No all-material-retained terminal-image claim.',
            'Native output velocity is staggered; this is a density/mass diagnostic, not velocity-at-header-time validation.',
            'All native states retained. Plot uses actual times; scalar peak difference uses stated interpolation onto0:0.05:5.'])
    save(dest/'report.json',report)
    fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
    for c,color,style,label in zip(cases,('#0072B2','#D55E00'),('-','--'),('Sharp velocity','Historical tanh velocity')):
        ax.plot([r['t_over_tcc'] for r in c['series']],[r['dense_mass_over_initial'] for r in c['series']],color=color,ls=style,label=label)
    ax.set(title='GIZMO MFM | initial L3 | chi=100, Mach 2\nSingle-resolution pilot; original periodic boundaries',
           xlabel=r'$t/t_{cc}$',ylabel='Dense mass / initial dense mass',xlim=(0,5),ylim=(0,1.1))
    ax.grid(alpha=.2);ax.legend();ax.spines[['top','right']].set_visible(False)
    fig.savefig(dest/'mass_mfm_L3.png',dpi=180);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k!='series'},indent=2))

if __name__=='__main__':main()
