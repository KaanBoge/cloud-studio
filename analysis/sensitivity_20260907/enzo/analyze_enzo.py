"""Independent HDF5 sums for every completed native Enzo control snapshot."""
import gc
import json
from pathlib import Path
import re
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_enzo import ROOT,raw,pair_initial,save,sha,parse_file

def direct(snapshot,params,dims):
    n=int(np.prod(dims));dv=2000/n;dense=tracer=0.;cells=0
    files=sorted(Path(snapshot).parent.glob(Path(snapshot).name+'.cpu*'))
    if len(files)!=8:raise ValueError('Expected eight native MPI HDF5 files')
    for p in files:
        with h5py.File(p) as h:
            for key in h:
                g=h[key]
                # Enzo writes a non-cell Metadata group beside GridNNNNNNNN.
                if key=='Metadata':
                    if not isinstance(g,h5py.Group):raise ValueError('Invalid Metadata type')
                    continue
                if not isinstance(g,h5py.Group) or not key.startswith('Grid'):raise ValueError('Unexpected HDF5 layout')
                if set(g)!=set(('Density','Metal_Density','TotalEnergy','x-velocity','y-velocity','z-velocity')):raise ValueError('Unexpected fields')
                d={k:g[k][...] for k in g}
                if any(a.dtype!=np.float64 or not np.all(np.isfinite(a)) for a in d.values()):raise ValueError('Precision/nonfinite field mismatch')
                rho=d['Density'];pressure=(params['gamma']-1)*rho*(d['TotalEnergy']-.5*sum(d[a+'-velocity']**2 for a in 'xyz'))
                if rho.min()<=0 or pressure.min()<=0:raise ValueError('Nonpositive density/pressure')
                dense+=float(rho[rho>params['chi']*params['rho_wind']/3].sum())*dv
                tracer+=float(d['Metal_Density'].sum())*dv;cells+=rho.size
    if cells!=n:raise ValueError('Incomplete native cell count')
    metadata=Path(snapshot).read_text()
    matches=re.findall(r'(?m)^InitialTime\s*=\s*(\S+)',metadata)
    if len(matches)!=1:raise ValueError('Missing/ambiguous native time')
    return dict(dense_mass=dense,tracer_mass=tracer,time_code=float(matches[0]),cells=cells)

def curve_delta(sharp,historical):
    grid=np.linspace(0,5,101)
    if any(not np.all(np.diff([r['t_over_tcc'] for r in s])>0) for s in (sharp,historical)):raise ValueError('Nonmonotonic native times')
    curves=[np.interp(grid,[r['t_over_tcc'] for r in s],[r['dense_mass_over_initial'] for r in s]) for s in (sharp,historical)]
    return float(np.max(np.abs(curves[0]-curves[1])))

def main():
    batch=json.loads((ROOT/'batch_v2.json').read_text())
    records={(r['level'],r['mode']):r for r in batch['finished']}
    if set(records)!={(l,m) for l in (3,4) for m in (0,1)}:raise ValueError('Unexpected completed scope')
    dest=ROOT/'analysis'
    if dest.exists() and any(dest.iterdir()):raise ValueError('Analysis output already exists')
    dest.mkdir(exist_ok=True);series={};pairs=[];checks=[]
    for level in (3,4):
        dims=[8*2**level,4*2**level,4*2**level]
        a,b=[records[level,m] for m in (0,1)];ic=pair_initial(a,b)
        for r in (a,b):
            p=Path(r['directory'])/'CloudWind.enzo'
            if sha(p)!=r['parameter_sha256']:raise ValueError('Input changed')
            params=parse_file(p);rows=[];maxerr=0.
            for old in r['series']:
                got=direct(old['snapshot'],params,dims)
                for key in ('dense_mass','tracer_mass'):
                    err=abs(got[key]-old[key])/max(abs(old[key]),1.)
                    maxerr=max(maxerr,err)
                    if err>1e-12:raise ValueError('Native HDF5 vs yt mass discrepancy')
                if abs(got['time_code']-old['time_code'])>1e-12:raise ValueError('Native time discrepancy')
                rows.append(dict(old))
            series[Path(r['directory']).name]=rows
            checks.append(dict(level=level,mode=r['mode'],snapshots=len(rows),maximum_scaled_mass_error=maxerr))
            print(f'Cross-checked Enzo L{level}, mode={r["mode"]}, {len(rows)} native snapshots',flush=True)
        s,h=[series[Path(r['directory']).name] for r in (a,b)]
        if s[0]['dense_mass']!=h[0]['dense_mass'] or s[0]['tracer_mass']!=h[0]['tracer_mass']:raise ValueError('Initial denominators differ')
        pairs.append(dict(level=level,initial_checks=ic,max_abs_curve_delta_over_initial_mass=curve_delta(s,h),
            sharp_final_dense_fraction=s[-1]['dense_mass_over_initial'],historical_final_dense_fraction=h[-1]['dense_mass_over_initial'],
            sharp_final_tracer_fraction=s[-1]['tracer_mass_over_initial'],historical_final_tracer_fraction=h[-1]['tracer_mass_over_initial'],
            frames_per_variant=[len(s),len(h)],wall_seconds=[a['wall_seconds'],b['wall_seconds']],
            peak_solver_child_rss_gib=max(a['peak_child_rss_gib'],b['peak_child_rss_gib'])))
    report=dict(status='share_with_caveats',code='Enzo',chi=100,mach=2,pairs=pairs,series=series,
        independent_HDF5_checks=checks,source_batch_sha256=sha(ROOT/'batch_v2.json'),analysis_sha256=sha(__file__),
        methodology='rho>rho_cloud_initial/3, fixed native initial dense mass. Actual native times plotted. Curve separation linearly interpolates scalar diagnostics to 0:0.05:5 t_cc only.',
        caveats=['L3/L4 only; L5 pair storage-held, no convergence or universal historical reuse decision.',
        'All 102 actual native times per run are retained, including the extra terminal dump.',
        'Tracer loss means t=5 is not a certified all-material-retained figure time.',
        'Full native fields remain on disk; derived figures are not raw backups.'])
    save(dest/'report.json',report)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for level,color in ((3,'#0072B2'),(4,'#D55E00')):
        for mode,style,label in ((0,'-','sharp'),(1,'--','historical')):
            ss=series[Path(records[level,mode]['directory']).name]
            for ax,key in zip(axes,('dense_mass_over_initial','tracer_mass_over_initial')):
                ax.plot([r['t_over_tcc'] for r in ss],[r[key] for r in ss],color=color,ls=style,label=f'L{level} {label}')
    for ax,title in zip(axes,('Density-selected mass','Tracer mass remaining in box')):
        ax.set(title=title,xlabel=r'$t/t_{cc}$',ylabel='Mass / respective initial mass',xlim=(0,5),ylim=(0,1.08));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Enzo velocity sensitivity | chi=100, Mach 2 | all native times')
    fig.savefig(dest/'mass_and_retention.png',dpi=180);plt.close(fig)
    print(json.dumps(pairs,indent=2),flush=True)

if __name__=='__main__':main()
