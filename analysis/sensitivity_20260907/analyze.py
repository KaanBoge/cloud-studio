"""Within-code paired IC diagnostics from full native 3D fields.

Figures show native times. Only scalar diagnostic curves are linearly interpolated
for explicitly labeled common-time differences; no volume/frame interpolation.
Final morphology uses the actual common terminal time, 5 t_cc. Cloud retention
is reported, not assumed. Coarse L3/L4 tests cannot certify finer resolutions.
"""
import json
from pathlib import Path
import sys
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_pairs import ROOT, OLD, LEVELS, native, outputs, without_mode, sha


def metrics(data,params,code):
    rho=data['rho'];dv=data['dv'];mass=rho*dv
    dense=rho>params['chi']*params['rho_wind']/3
    dm=float(np.sum(mass[dense]));axis=0 if code=='athpp' else 1
    coord=np.broadcast_to(data['coord'][axis],rho.shape)
    return dict(time_code=data['time'],t_over_tcc=data['time']/params['t_cc'],
        dense_mass=dm,tracer_mass=float(np.sum(mass*data['c'])),
        total_mass=float(mass.sum()),density_max=float(rho.max()),
        dense_centroid_R=float(np.sum(mass[dense]*coord[dense])/dm/params['r_cloud']) if dm>0 else None)


def series(record):
    folder=Path(record['directory']);code=record['code'];rows=[]
    for t,path in outputs(folder,code):
        data=native(path,code);row=metrics(data,record['parameters'],code)
        row.update(snapshot=path.name,snapshot_sha256=sha(path))
        if rows and t<=rows[-1]['time_code']:raise ValueError('Duplicate/unordered native time')
        rows.append(row)
    if len(rows)!=101 or abs(rows[0]['t_over_tcc'])>1e-10 or abs(rows[-1]['t_over_tcc']-5)>1e-8:
        raise ValueError('Incomplete native time series')
    m0=rows[0]['dense_mass'];c0=rows[0]['tracer_mass']
    if m0<=0 or c0<=0:raise ValueError('Unresolved initial denominator')
    for row in rows:
        row['dense_mass_over_initial']=row['dense_mass']/m0
        row['tracer_mass_over_initial']=row['tracer_mass']/c0
    return rows


def exact_pair_initial(historical,sharp):
    for key in ('rho','c'):
        if not np.array_equal(historical[key],sharp[key]):raise ValueError('Changed initial '+key)
    for a,b in zip(historical['faces'],sharp['faces']):
        if not np.array_equal(a,b):raise ValueError('Changed mesh coordinates')
    # Recovering pressure from total energy incurs rounding after changing vx.
    pe=float(np.max(np.abs(historical['p']-sharp['p'])))
    if pe>1e-10:raise ValueError('Changed equilibrium pressure')
    dv=max(float(np.max(np.abs(a-b))) for a,b in zip(historical['v'],sharp['v']))
    if dv<1e-8:raise ValueError('Velocity prescription did not actually change')
    return dict(density_and_tracer_exact=True,coordinates_exact=True,
                pressure_absolute_difference_max=pe,velocity_absolute_difference_max=dv)


def volume(data,code):
    """Reassemble uniform leaf cells without interpolation or duplicated cells."""
    dims=data['dims'];grid=np.full(dims,np.nan)
    edges=[q.min() for q in data['faces']]
    delta=[np.diff(q,axis=1)[0,0] for q in data['faces']]
    for b in range(data['rho'].shape[0]):
        ids=[np.rint((q[b]-e)/dx-.5).astype(int) for q,e,dx in zip(data['centers'],edges,delta)]
        idx=np.ix_(*ids)
        if np.any(np.isfinite(grid[idx])):raise ValueError('Duplicate cells in assembled volume')
        grid[idx]=data['rho'][b].transpose(2,1,0)
    if not np.all(np.isfinite(grid)):raise ValueError('Missing cells')
    return grid if code=='athpp' else grid.transpose(1,0,2)


def independent_yt(record,expected):
    import yt
    yt.set_log_level(40)
    path=Path(record['directory'])/expected['snapshot']
    ds=yt.load(str(path));ad=ds.all_data()
    rho=ad['gas','density'].to_value('code_density')
    dv=ad['index','cell_volume'].to_value('code_length**3')
    threshold=record['parameters']['chi']*record['parameters']['rho_wind']/3
    m=float(np.sum((rho*dv)[rho>threshold]))
    err=abs(m-expected['dense_mass'])/max(abs(m),1e-100)
    if err>1e-10:raise ValueError('Independent yt mass check failed')
    return dict(snapshot=str(path),direct_dense_mass=expected['dense_mass'],yt_dense_mass=m,relative_error=err)


def main():
    batch=json.loads((ROOT/'batch.json').read_text())
    if batch['status']!='complete_native_checks':raise ValueError('Pilot is incomplete')
    destination=ROOT/'analysis'
    destination.mkdir(exist_ok=False)
    records={(x['code'],x['level'],x['velocity_ic']):x for x in batch['finished']}
    all_series={};pairs=[];slices=[];yt_checks=[]
    for code in OLD:
        for level in LEVELS:
            a=records[code,level,OLD[code]];b=records[code,level,'sharp13']
            if a['binary_sha256']!=b['binary_sha256']:raise ValueError('Pair binaries differ')
            ta=(Path(a['directory'])/'athinput').read_text();tb=(Path(b['directory'])/'athinput').read_text()
            if without_mode(ta)!=without_mode(tb):raise ValueError('Parameters differ beyond velocity_ic')
            for rec in (a,b):
                all_series[Path(rec['directory']).name]=series(rec)
            sa=all_series[Path(a['directory']).name];sb=all_series[Path(b['directory']).name]
            da0=native(Path(a['directory'])/sa[0]['snapshot'],code);db0=native(Path(b['directory'])/sb[0]['snapshot'],code)
            ic=exact_pair_initial(da0,db0)
            if sa[0]['dense_mass']!=sb[0]['dense_mass']:raise ValueError('Initial mass denominator changed')
            grid=np.linspace(0,5,101)
            ma=np.interp(grid,[x['t_over_tcc'] for x in sa],[x['dense_mass_over_initial'] for x in sa])
            mb=np.interp(grid,[x['t_over_tcc'] for x in sb],[x['dense_mass_over_initial'] for x in sb])
            da=native(Path(a['directory'])/sa[-1]['snapshot'],code);db=native(Path(b['directory'])/sb[-1]['snapshot'],code)
            if abs(da['time']-db['time'])>1e-10:raise ValueError('Final native times differ')
            va=volume(da,code);vb=volume(db,code)
            delta=float(sb[-1]['dense_mass_over_initial']-sa[-1]['dense_mass_over_initial'])
            ah=sa[-1]['dense_mass_over_initial']
            cb=[sa[-1]['dense_centroid_R'],sb[-1]['dense_centroid_R']]
            pair=dict(code=code,level=level,chi=100,mach=2,historical_law=OLD[code],
                initial_pair_checks=ic,same_binary_and_only_velocity_input_differs=True,
                dimensions_streamwise=list(va.shape),native_frames_per_variant=101,
                terminal_t_over_tcc=sa[-1]['t_over_tcc'],
                historical_final_dense_mass_over_initial=ah,
                sharp_final_dense_mass_over_initial=sb[-1]['dense_mass_over_initial'],
                final_delta_in_units_initial_dense_mass=delta,
                final_relative_change_percent=100*delta/ah if ah>0 else None,
                max_abs_curve_delta_in_units_initial_dense_mass=float(np.max(np.abs(mb-ma))),
                scalar_curve_alignment='Linear interpolation of scalar mass diagnostics only onto 0:0.05:5 t_cc; raw times retained.',
                aligned_time_grid=grid.tolist(),aligned_sharp_minus_historical_mass=(mb-ma).tolist(),
                dense_centroid_difference_R=cb[1]-cb[0] if all(v is not None for v in cb) else None,
                final_density_L1_over_historical_box_mass=float(np.sum(np.abs(vb-va))/np.sum(va)),
                historical_tracer_fraction_in_box=sa[-1]['tracer_mass_over_initial'],
                sharp_tracer_fraction_in_box=sb[-1]['tracer_mass_over_initial'],
                retention_warning='Net tracer mass is not proof of zero boundary loss; t=5 is a shared terminal time, not a certified all-material-retained time.')
            pairs.append(pair)
            slices.append((pair,va[:,:,va.shape[2]//2-1:va.shape[2]//2+1].mean(axis=2),
                           vb[:,:,vb.shape[2]//2-1:vb.shape[2]//2+1].mean(axis=2)))
            if level==3:
                for rec,ss in ((a,sa),(b,sb)):
                    yt_checks.extend([independent_yt(rec,ss[0]),independent_yt(rec,ss[-1])])
    result=dict(scope='Pilot: two codes at L3/L4, chi=100, Mach 2. Not a universal decision about historical reuse.',
        definition='Dense means rho > rho_cloud_initial/3; normalized by the unchanged measured native M_dense(0).',
        pairs=pairs,series=all_series,independent_yt_checks=yt_checks,
        required_caveats=['Only velocity changes within each code pair; tracer and native axis differ between codes.',
          'L3/L4 have 3.2/6.4 cells per R: density/velocity edge behavior is underresolved and requires finer confirmation.',
          'Finite box and tracer loss can contribute to late-time differences.',
          'No claim of negligible impact, convergence, all-code comparability or suitability for a paper based on this pilot alone.',
          'Existing historical runs still require individual provenance checks before reuse.'])
    (destination/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),sharey=True,layout='constrained')
    for ax,(code,label) in zip(axs,[('athpp','Athena++'),('apk','AthenaPK')]):
        for level,color in zip(LEVELS,['#0072B2','#D55E00']):
            for mode,style in [(OLD[code],'--'),('sharp13','-')]:
                rr=records[code,level,mode];ss=all_series[Path(rr['directory']).name]
                ax.plot([x['t_over_tcc'] for x in ss],[x['dense_mass_over_initial'] for x in ss],
                        color=color,ls=style,lw=1.6,label=f"L{level} {'historical' if mode!='sharp13' else 'corrected'}")
        ax.set(title=label,xlabel=r'$t / t_{cc}$',xlim=(0,5),ylim=(0,None));ax.grid(alpha=.2);ax.legend(fontsize=8)
    axs[0].set_ylabel(r'$M_{dense}(t) / M_{dense}(0)$')
    fig.suptitle(r'Velocity-IC sensitivity pilot: $\chi=100$, Mach 2 | native output times')
    fig.savefig(destination/'mass_evolution.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(4,2,figsize=(12,11),layout='constrained',sharex=True,sharey=True)
    for row,(pair,a,b) in enumerate(slices):
        for col,(arr,label) in enumerate([(a,'historical'),(b,'corrected sharp velocity')]):
            ax=axs[row,col]
            im=ax.imshow(np.log10(np.maximum(arr/100,1e-12)).T,origin='lower',extent=(-3,17,-5,5),
                         cmap='viridis',vmin=-3.2,vmax=.4,interpolation='nearest',aspect='equal')
            ax.set_title(f"{pair['code']} L{pair['level']} | {label} | t = 5 t_cc",fontsize=10)
            if col==0:ax.set_ylabel('transverse / R')
            if row==3:ax.set_xlabel('streamwise / R')
    fig.colorbar(im,ax=axs.ravel().tolist(),shrink=.65,label=r'$\log_{10}(\rho/\rho_{cloud,initial})$')
    fig.suptitle('3D density rendered in 2D: mean of two central z cell planes\nCommon terminal time; not certified free of cloud-material escape',fontsize=12)
    fig.savefig(destination/'density_slices_t5.png',dpi=170);plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ('series',)},indent=2),flush=True)


if __name__=='__main__':main()
