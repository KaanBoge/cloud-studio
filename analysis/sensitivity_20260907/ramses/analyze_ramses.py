"""Native RAMSES density-mass/retention overlays at the observed output times.

Second aggregation uses unsorted native leaf records and blockwise sums; it is
independent of grid assembly, but shares the audited Fortran-record reader.
"""
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_ramses import ROOT,sha,save,pair_initial,read_output,parameters

def second_aggregation(c,p):
    if c.ndim!=2 or c.shape[1]!=10 or not np.all(np.isfinite(c)):raise ValueError('Invalid native cells')
    dense=[];tracer=[];total=[]
    for group in np.array_split(c,32):
        mass=group[:,4]*group[:,3]**3
        dense.append(float(mass[group[:,4]>p['chi']*p['rho_wind']/3].sum()))
        tracer.append(float((mass*group[:,9]).sum()));total.append(float(mass.sum()))
    return dict(dense_mass=math.fsum(dense),tracer_mass=math.fsum(tracer),total_mass=math.fsum(total))

def crosscheck(row,p):
    meta,c=read_output(row['snapshot'])
    if len(c)!=row['cells'] or meta['time']!=row['time_code']:raise ValueError('Native time/cell mismatch')
    masses=second_aggregation(c,p)
    error=max(abs(v-row[k])/max(abs(row[k]),1.) for k,v in masses.items())
    if error>1e-12:raise ValueError('Second native aggregation disagrees')
    return error

def main():
    batch=json.loads((ROOT/'batch.json').read_text())
    if batch['status'] not in ('held_storage','complete_native_checks'):raise ValueError('Worker still running or needs review')
    records={(r['level'],r['mode']):r for r in batch['finished']}
    if set(records)!={(l,m) for l in (3,4) for m in (0,1)}:raise ValueError('Unexpected completed scope; review before analysis')
    dest=ROOT/'analysis';dest.mkdir(exist_ok=False);pairs=[];series={}
    for level in (3,4):
        a,b=[records[level,m] for m in (0,1)];checks=pair_initial(a,b);errors=[]
        for case in (a,b):
            source=Path(case['directory'])/'run.nml'
            if sha(source)!=case['parameter_sha256']:raise ValueError('Input changed')
            p=parameters(source);ss=case['series']
            if len(ss) not in (101,102) or not np.all(np.diff([r['time_code'] for r in ss])>0):raise ValueError('Bad native cadence')
            errors.append(max(crosscheck(row,p) for row in ss))
            series[Path(case['directory']).name]=ss
        for quantity in ('dense_mass','tracer_mass'):
            if a['series'][0][quantity]!=b['series'][0][quantity]:raise ValueError('Initial denominator changed')
        grid=np.linspace(0,5,101)
        curves=[np.interp(grid,[r['t_over_tcc'] for r in c['series']],[r['dense_mass_over_initial'] for r in c['series']]) for c in (a,b)]
        rss=[r['peak_child_rss_gib'] for r in (a,b) if r['peak_child_rss_gib'] is not None]
        pairs.append(dict(level=level,frames_per_variant=[a['unique_snapshots'],b['unique_snapshots']],initial_checks=checks,
            max_abs_curve_delta_over_initial_mass=float(np.max(abs(curves[0]-curves[1]))),
            final_dense_fractions=[r['series'][-1]['dense_mass_over_initial'] for r in (a,b)],
            final_tracer_retention=[r['series'][-1]['tracer_mass_over_initial'] for r in (a,b)],
            final_actual_t_over_tcc=[r['series'][-1]['t_over_tcc'] for r in (a,b)],
            second_aggregation_max_scaled_error=max(errors),wall_seconds=[r['wall_seconds'] for r in (a,b)],
            sampled_peak_solver_child_rss_gib=max(rss) if rss else None))
    report=dict(status='share_with_caveats',code='RAMSES',chi=100,mach=2,pairs=pairs,series=series,
        source_batch_sha256=sha(ROOT/'batch.json'),analysis_sha256=sha(__file__),
        methodology='All actual native leaf-cell outputs; rho>rho_cloud_initial/3 with a fixed measured initial denominator. Plot native times unchanged. Only scalar curve separation uses linear interpolation to 0:0.05:5 t_cc.',
        caveats=['L3/L4 are coarse within-code controls, not convergence or a universal reuse decision.',
        'Native timestep-crossing output times can be slightly later than nominal times; no snapshots were retimed.',
        'Tracer retention is measured, not assumed. Final images need not retain all initial material.',
        'The second aggregation shares the native record decoder; stock yt does not support this rectangular patch correctly.',
        'L5 depends on full raw-retention storage. No raw files have been deleted.'])
    save(dest/'report.json',report)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for level,color in ((3,'#0072B2'),(4,'#D55E00')):
        for mode,style,name in ((0,'-','sharp'),(1,'--','historical')):
            ss=records[level,mode]['series'];t=[r['t_over_tcc'] for r in ss]
            for ax,key in zip(axes,('dense_mass_over_initial','tracer_mass_over_initial')):
                ax.plot(t,[r[key] for r in ss],color=color,ls=style,label=f'L{level} {name}')
    for ax,title,ylabel in zip(axes,('Density-selected mass','Tracer mass remaining in box'),
                               (r'$M_{dense}(t)/M_{dense}(0)$',r'$M_{tracer}(t)/M_{tracer}(0)$')):
        ax.set(title=title,xlabel=r'$t/t_{cc}$',ylabel=ylabel,xlim=(0,5.02),ylim=(0,1.08))
        ax.grid(alpha=.2);ax.legend(fontsize=9)
    fig.suptitle('RAMSES velocity sensitivity | chi=100, Mach 2 | actual native times')
    fig.savefig(dest/'mass_and_retention.png',dpi=180);plt.close(fig)
    print(json.dumps(pairs,indent=2),flush=True)

if __name__=='__main__':main()
