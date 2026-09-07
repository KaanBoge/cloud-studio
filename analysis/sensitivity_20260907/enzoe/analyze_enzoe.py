"""Paired native Enzo-E mass analysis; no tracer-based retention claim."""
import json
from pathlib import Path
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_enzoe import ROOT,sha,save,pair_check,snapshot,params_for

def independent_mass(row,params):
    total=0.;count=0
    for filename in row['files']:
        with h5py.File(filename) as h:
            for g in h.values():
                start=g.attrs['enzo_GridStartIndex'];end=g.attrs['enzo_GridEndIndex']+1
                region=tuple(slice(int(start[i]),int(end[i])) for i in (2,1,0))
                rho=g['field_density'][region]
                dv=float(np.prod(g.attrs['enzo_CellWidth']))
                total+=float(rho[rho>params['chi']/3].sum())*dv;count+=rho.size
    if count!=np.prod(params['dimensions']):raise ValueError('Wrong independent cell count')
    error=abs(total-row['dense_mass'])/max(abs(row['dense_mass']),1.)
    if error>1e-12:raise ValueError('Per-block mass does not match assembled-grid sum')
    return error

def main():
    batch=json.loads((ROOT/'batch.json').read_text());records={(r['level'],r['mode']):r for r in batch['finished']}
    if set(records)!={(l,m) for l in (3,4) for m in (0,1)}:raise ValueError('Unexpected completed scope')
    dest=ROOT/'analysis';dest.mkdir(exist_ok=False);pairs=[];series={}
    for l in (3,4):
        a,b=[records[l,m] for m in (0,1)];checks=pair_check(a,b)
        initials=[snapshot([Path(p) for p in r['series'][0]['files']],r['parameters'],True,r['mode'],True) for r in (a,b)]
        pe=float(np.max(abs(initials[0][2]-initials[1][2])))
        if pe>1e-10:raise ValueError('Initial pair pressure differs beyond double-precision recovery tolerance')
        errors=[]
        for r in (a,b):
            p=Path(r['directory'])/'cloud.in'
            if sha(p)!=r['input_sha256']:raise ValueError('Input changed')
            params=params_for(p.read_text());ss=r['series']
            if len(ss)!=101 or not np.all(np.diff([x['time_code'] for x in ss])>0):raise ValueError('Incomplete/repeated output')
            errors.append(max(independent_mass(row,params) for row in ss))
            series[Path(r['directory']).name]=ss
        if a['series'][0]['dense_mass']!=b['series'][0]['dense_mass']:raise ValueError('Initial denominator differs')
        grid=np.linspace(0,5,101)
        curves=[np.interp(grid,[x['t_over_tcc'] for x in r['series']],[x['dense_mass_over_initial'] for x in r['series']]) for r in (a,b)]
        pairs.append(dict(level=l,frames_per_variant=101,initial_checks=checks,initial_pressure_max_difference=pe,
            max_abs_curve_delta_over_initial_mass=float(np.max(abs(curves[0]-curves[1]))),
            sharp_final_dense_fraction=a['series'][-1]['dense_mass_over_initial'],historical_final_dense_fraction=b['series'][-1]['dense_mass_over_initial'],
            independent_max_scaled_mass_error=max(errors),wall_seconds=[a['wall_seconds'],b['wall_seconds']],
            peak_solver_rss_gib=max(a['peak_solver_rss_gib'],b['peak_solver_rss_gib']),tracer_retention=None))
    report=dict(status='share_with_caveats',code='Enzo-E',chi=100,mach=2,pairs=pairs,series=series,
        source_batch_sha256=sha(ROOT/'batch.json'),analysis_sha256=sha(__file__),
        methodology='All 404 native snapshots; native active-cell mass sums with ghost cells excluded. Dense rho>rho_cloud_initial/3, fixed native initial denominator. Plot actual times; scalar difference linearly interpolated onto 0:0.05:5 t_cc.',
        caveats=['No passive tracer in either native recipe; material retention is not measured.',
        'L3/L4 only; L5 pair storage-held. No universal historical reuse or convergence decision.',
        'Historical radial law from 2D input is tested spherically in the audited 3D setup.'])
    save(dest/'report.json',report)
    fig,ax=plt.subplots(figsize=(8,4.7),layout='constrained')
    for l,color in ((3,'#0072B2'),(4,'#D55E00')):
        for mode,style,label in ((0,'-','sharp'),(1,'--','historical')):
            ss=records[l,mode]['series'];ax.plot([r['t_over_tcc'] for r in ss],[r['dense_mass_over_initial'] for r in ss],color=color,ls=style,label=f'L{l} {label}')
    ax.set(title='Enzo-E velocity sensitivity | chi=100, Mach 2\nNative times; no tracer-based retention diagnostic',xlabel=r'$t/t_{cc}$',ylabel=r'$M_{dense}(t)/M_{dense}(0)$',xlim=(0,5),ylim=(0,1.08));ax.grid(alpha=.2);ax.legend()
    fig.savefig(dest/'mass_evolution.png',dpi=180);plt.close(fig);print(json.dumps(pairs,indent=2),flush=True)

if __name__=='__main__':main()
