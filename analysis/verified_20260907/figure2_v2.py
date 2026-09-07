"""Overplot resolutions from schema-2 dense-mass diagnostics, never legacy fractions.

All inputs must belong to one explicitly reviewed comparison group. Legend
resolution comes from measured cells, not filename labels or a command-line level.
This plots density-selected gas, not tracer mass or a cooling-temperature selection.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from comparison_checks import require_common_physics


def load_runs(paths):
    runs=[]
    for path in paths:
        d=json.loads(Path(path).read_text())
        if d.get('schema_version')!=2:
            raise ValueError(f'{path}: legacy diagnostics must be recomputed from native outputs')
        t=np.array([r['t_over_tcc'] for r in d['series']])
        m=np.array([r['dense_mass_over_initial_dense_mass'] for r in d['series']])
        if len(t)<2 or not np.all(np.isfinite(t)) or not np.all(np.isfinite(m)):
            raise ValueError(f'{path}: insufficient/invalid measured samples')
        if np.any(m<0):
            raise ValueError(f'{path}: negative normalized mass')
        if abs(t[0])>1e-10 or abs(m[0]-1)>1e-10 or np.any(np.diff(t)<=0):
            raise ValueError(f'{path}: invalid initial value or time ordering')
        if not d.get('comparison_group') or not d.get('initial_grid'):
            raise ValueError(f'{path}: missing comparison/resolution metadata')
        runs.append(d)
    if len({d['comparison_group'] for d in runs})!=1:
        raise ValueError('Do not mix IC, Mach, boundary or cooling groups')
    require_common_physics(runs)
    return runs


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    ap.add_argument('diagnostics',nargs='+')
    a=ap.parse_args()
    out=Path(a.out)
    if out.exists(): raise FileExistsError('Use a new output filename')
    runs=load_runs(a.diagnostics)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    chis=sorted({d['parameters']['chi'] for d in runs})
    fig,axes=plt.subplots(1,len(chis),squeeze=False,figsize=(5*len(chis),4.8),sharey=True)
    codes=sorted({d['kind'] for d in runs})
    colors=dict(zip(codes,plt.get_cmap('tab20').colors))
    # Code is colour; resolution is linestyle, as in a convergence figure.
    resolutions=sorted({tuple(d['initial_grid']['finest_equivalent_dimensions']) for d in runs})
    patterns=['-', '--', '-.', ':', (0,(5,1,1,1)), (0,(3,1,1,1,1,1))]
    styles={dims:patterns[i%len(patterns)] for i,dims in enumerate(resolutions)}
    for ax,chi in zip(axes[0],chis):
        for d in sorted(runs,key=lambda x:(x['kind'],x['initial_grid']['finest_equivalent_dimensions'])):
            if d['parameters']['chi']!=chi: continue
            grid=d['initial_grid']; dims=grid['finest_equivalent_dimensions']
            style='uniform' if grid['uniform'] else 'finest equivalent; AMR'
            label=f"{d['kind']}: {' x '.join(map(str,dims))} ({style})"
            t=[r['t_over_tcc'] for r in d['series']]
            m=[r['dense_mass_over_initial_dense_mass'] for r in d['series']]
            width=.8+np.log2(max(dims)/16+1)*.35
            ax.plot(t,m,label=label,color=colors[d['kind']],lw=width,linestyle=styles[tuple(dims)])
        ax.set_title(f'chi = {chi:g}')
        ax.set_xlabel('t / t_cc'); ax.grid(alpha=.2)
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.set_ylim(0,max(1.05,max(r['dense_mass_over_initial_dense_mass'] for d in runs for r in d['series'])*1.05))
        ax.legend(fontsize=7)
    axes[0][0].set_ylabel('M_dense(t) / M_dense(0), rho > rho_cloud,0 / 3')
    fig.suptitle(runs[0]['comparison_group'])
    fig.tight_layout(); fig.savefig(out,dpi=170)


if __name__=='__main__': main()
