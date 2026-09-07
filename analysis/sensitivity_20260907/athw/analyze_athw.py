"""Native Athena 4.2 paired-field and tracer QA; never rewrites raw data.

Dense mass is rho > initial cloud density/3, normalized to native t=0.
Tracer mass uses the native specific_scalar[0] * rho * cell volume.
Scalar interpolation is only for curve separation, not manufactured snapshots.
"""
import gc
import json
import re
from pathlib import Path
import sys
import numpy as np
import yt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent))
from run_athw import ROOT, sha, save
yt.set_log_level(40)

def no_mode(text):
    if len(re.findall(r'(?m)^velocity_ic_tanh = [01]$',text))!=1:
        raise ValueError('Ambiguous velocity switch')
    return re.sub(r'(?m)^velocity_ic_tanh = [01]$','',text)

def native(path, full=False):
    ds=yt.load(str(path));ad=ds.all_data()
    rho=ad['gas','density'].to_value('code_density')
    dv=ad['index','cell_volume'].to_value('code_length**3')
    tracer=ad['athena','specific_scalar[0]'].to_value('dimensionless')
    if not all(np.all(np.isfinite(a)) for a in (rho,dv,tracer)):
        raise ValueError('Nonfinite native tracer/field')
    result=dict(time=float(ds.current_time.to_value('code_time')),
                rho=rho,dv=dv,tracer=tracer)
    if full:
        result['xyz']=np.stack([ad['index',a].to_value('code_length') for a in 'xyz'],axis=1)
        result['pressure']=ad['gas','pressure'].to_value('code_pressure')
        result['vel']=np.stack([ad['gas','velocity_'+a].to_value('code_velocity') for a in 'xyz'],axis=1)
    return result

def initial_pair(a,b):
    for key in ('rho','dv','tracer','xyz'):
        if not np.array_equal(a[key],b[key]):raise ValueError('Pair differs in '+key)
    pe=float(np.max(np.abs(a['pressure']-b['pressure'])))
    if pe>3e-6:raise ValueError('Initial pressure mismatch')
    f=.5*(1-np.tanh((np.linalg.norm(a['xyz'],axis=1)-1)/.1))
    expected=100*f/(1+99*f)
    te=float(np.max(np.abs(a['tracer']-expected)))
    if te>3e-6:raise ValueError('Native tracer does not match conserved scalar chi*f')
    vd=float(np.max(np.abs(a['vel']-b['vel'])))
    if vd<1e-8:raise ValueError('Velocity did not change')
    return dict(density_tracer_coordinates_volumes_exact=True,
        pressure_max_absolute_difference=pe,tracer_analytic_max_absolute_error=te,
        velocity_max_absolute_difference=vd)

def mass_metrics(data,threshold):
    mass=data['rho']*data['dv']
    return float(mass[data['rho']>threshold].sum()),float(np.dot(mass,data['tracer']))

def main():
    batch=json.loads((ROOT/'batch.json').read_text())
    if batch['status']!='complete_native_checks' or len(batch['finished'])!=6:
        raise ValueError('Incomplete batch')
    destination=ROOT/'analysis';destination.mkdir(exist_ok=False)
    pairs=[];all_series={};records={(r['level'],r['mode']):r for r in batch['finished']}
    for level in (3,4,5):
        recs=[records[level,m] for m in (0,1)]
        if recs[0]['binary_sha256']!=recs[1]['binary_sha256']:raise ValueError('Different binaries')
        texts=[]
        for r in recs:
            inp=Path(r['directory'])/'athinput'
            if sha(inp)!=r['parameter_sha256']:raise ValueError('Input changed')
            texts.append(no_mode(inp.read_text()))
        if texts[0]!=texts[1]:raise ValueError('Other parameter differences')
        ic=initial_pair(*[native(r['series'][0]['snapshot'],True) for r in recs]);gc.collect()
        pair_series=[]
        for r in recs:
            rows=[];threshold=r['parameters']['rho_wind']*r['parameters']['chi']/3
            for i,prior in enumerate(r['series']):
                data=native(prior['snapshot']);dense,tracer=mass_metrics(data,threshold)
                if not np.isclose(dense,prior['dense_mass'],rtol=1e-12,atol=1e-12):
                    raise ValueError('Native dense mass differs from worker validation')
                if abs(data['time']-prior['time_code'])>1e-10:raise ValueError('Timestamp changed')
                if i==0:d0,t0=dense,tracer
                rows.append(dict(snapshot=prior['snapshot'],t_over_tcc=prior['t_over_tcc'],
                    dense_mass=dense,dense_mass_over_initial=dense/d0,
                    tracer_mass=tracer,tracer_mass_over_initial=tracer/t0,
                    tracer_min=float(data['tracer'].min()),tracer_max=float(data['tracer'].max())))
                del data;gc.collect()
            if len(rows)!=101 or not np.all(np.diff([x['t_over_tcc'] for x in rows])>0):
                raise ValueError('Missing or repeated native times')
            all_series[Path(r['directory']).name]=rows;pair_series.append(rows)
            print(f'Validated L{level} mode={r["mode"]}: {len(rows)} fields/times',flush=True)
        sharp,old=pair_series
        if sharp[0]['dense_mass']!=old[0]['dense_mass']:raise ValueError('Initial denominator differs')
        grid=np.linspace(0,5,101)
        curves=[np.interp(grid,[x['t_over_tcc'] for x in ss],[x['dense_mass_over_initial'] for x in ss]) for ss in pair_series]
        pairs.append(dict(level=level,initial_pair_checks=ic,frames_per_variant=101,
            max_abs_curve_delta_over_initial_mass=float(np.max(np.abs(curves[0]-curves[1]))),
            sharp_final_dense_fraction=sharp[-1]['dense_mass_over_initial'],
            historical_final_dense_fraction=old[-1]['dense_mass_over_initial'],
            sharp_final_tracer_fraction=sharp[-1]['tracer_mass_over_initial'],
            historical_final_tracer_fraction=old[-1]['tracer_mass_over_initial'],
            sharp_wall_seconds=recs[0]['wall_seconds'],historical_wall_seconds=recs[1]['wall_seconds'],
            peak_solver_child_rss_gib=max(r['peak_child_rss_gib'] for r in recs)))
    report=dict(status='share_with_caveats',code='Athena 4.2',chi=100,mach=2,
        source_batch_sha256=sha(ROOT/'batch.json'),analysis_sha256=sha(__file__),pairs=pairs,series=all_series,
        methodology='Within-code pairs; only velocity_ic_tanh changes. Dense rho>rho_cloud_initial/3. Fixed native M_dense(0). Curves plotted at actual times; scalar curve separation interpolated onto 0:0.05:5 t_cc.',
        caveats=['Three finite resolutions do not establish a universal reuse decision or convergence.',
        'Net tracer retention is not proof that no material crossed a boundary.',
        'Native VTK is float32; density/tracer equality is checked at this native precision.',
        'Tracer concentration is chi*f/rho in Athena 4.2, unlike the other codes; interpret within-code pairs.'])
    save(destination/'report.json',report)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for level,color in zip((3,4,5),('#0072B2','#D55E00','#009E73')):
        for mode,style,label in ((0,'-','sharp'),(1,'--','historical')):
            ss=all_series[Path(records[level,mode]['directory']).name]
            for ax,metric in zip(axes,('dense_mass_over_initial','tracer_mass_over_initial')):
                ax.plot([x['t_over_tcc'] for x in ss],[x[metric] for x in ss],color=color,ls=style,label=f'L{level} {label}')
    for ax,title in zip(axes,('Density-selected mass','Tracer mass remaining in box')):
        ax.set(title=title,xlabel=r'$t/t_{cc}$',ylabel='Mass / respective initial mass',xlim=(0,5),ylim=(0,1.08));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Athena 4.2 velocity sensitivity | chi=100, Mach 2 | native times')
    fig.savefig(destination/'mass_and_retention.png',dpi=180);plt.close(fig)
    print(json.dumps(pairs,indent=2),flush=True)

if __name__=='__main__':main()
