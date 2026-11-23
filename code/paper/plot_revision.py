"""Replot published scalar reductions; never opens native simulation outputs.

Run with Python 3 and matplotlib. The input JSON files are unchanged saved
reductions. Every temperature-band mass uses its own measured initial dense mass.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 11,
                     'pdf.fonttype': 42, 'ps.fonttype': 42})

def save(fig, name):
    fig.savefig(FIG / (name + '.pdf'), bbox_inches='tight')
    plt.close(fig)

def main():
    curves = json.loads((ROOT / 'plot_series.json').read_text())
    order = [('athpp','Athena++'), ('apk','AthenaPK'), ('athw','Athena 4.2'),
             ('enzo','Enzo'), ('enzoe','Enzo-E'), ('ramses','RAMSES'),
             ('flash','FLASH 4.8'), ('flashx','Flash-X'), ('arepo','Arepo'),
             ('mfm','GIZMO MFM'), ('mfv','GIZMO MFV'), ('gadget4','GADGET-4*')]
    styles = {3:('#117a88',':',32),4:('#d17c1f','--',64),5:('#684c9c','-',128)}
    fig, axs = plt.subplots(4,3,figsize=(10,8),sharex=True,sharey=True,layout='constrained')
    for ax,(code,title) in zip(axs.flat,order):
        for row in sorted((r for r in curves if r['code']==code),key=lambda r:r['level']):
            color,style,n=styles[row['level']]
            ax.plot(row['times'],row['dense'],color=color,ls=style,lw=1.7,label=f'$n={n}$')
        ax.set(title=title,xlim=(0,5),ylim=(0,1.25))
        ax.grid(alpha=.18)
    handles={label:h for ax in axs.flat for h,label in zip(*ax.get_legend_handles_labels())}
    fig.legend(handles.values(),handles.keys(),ncol=3,loc='outside upper center',frameon=False)
    fig.supxlabel(r'$t/t_{\rm cc}$');fig.supylabel(r'$M_{\rm d}/M_{\rm d}(0)$')
    save(fig,'mass_histories')
    series=json.loads((ROOT/'diagnostic_series.json').read_text())
    keys=[('velocity_over_wind',r'$\langle v_\parallel\rangle_{\rm d}/v_{\rm w}$'),
          ('mix_mass',r'$M_{\rm int}/M_{\rm d}(0)$'),('covering',r'$f_{\rm cov,int}$'),
          ('radius',r'$R_{\rm eff}/R$'),('contrast',r'$\rho_{\rm d}/\rho_{\rm w,0}$'),
          ('tcc_inst_over_initial',r'$t_{\rm cc,eff}/t_{\rm cc}$')]
    for output,pairs in [('gizmo_diagnostics',[('MFM sharp','GIZMO MFM'),('MFV sharp','GIZMO MFV')]),
                         ('cooling_diagnostics',[('Cooling on','Cooling on'),('Cooling off','Cooling off')])]:
        fig,axs=plt.subplots(3,2,figsize=(9,7.4),sharex=True,layout='constrained')
        for ax,(key,label) in zip(axs.flat,keys):
            for (name,legend),color in zip(pairs,['#117a88','#d17c1f']):
                rows=series[name];initial=rows[0]['dense_mass']
                y=[r[key]/initial if key=='mix_mass' else r[key] for r in rows]
                ax.plot([r['t'] for r in rows],y,'.-',color=color,label=legend,lw=1.8,ms=5)
            ax.set(ylabel=label,xlim=(0,5));ax.grid(alpha=.18)
        fig.legend(*axs[0,0].get_legend_handles_labels(),ncol=2,loc='outside upper center',frameon=False)
        fig.supxlabel(r'$t/t_{\rm cc}$');save(fig,output)

if __name__=='__main__':
    main()
