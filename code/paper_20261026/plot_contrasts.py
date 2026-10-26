"""Replot the saved contrast reductions, including the new AthenaPK case."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
fig,axs=plt.subplots(1,2,figsize=(9,3),sharey=True,layout='constrained')
colors={'Enzo':'#117a88','Enzo-E':'#d17c1f','Athena++':'#4b854b','AthenaPK*':'#684c9c'}
for row in json.loads((ROOT/'contrast_series.json').read_text()):
    ax=axs[0 if row['chi']==10 else 1]
    ax.plot(row['times'],row['dense'],label=row['label'],lw=1.7,
            color=colors.get(row['label']),ls='--' if row['label']=='AthenaPK*' else '-')
for ax,chi in zip(axs,[10,1000]):
    ax.set(title=fr'$\chi={chi}$',xlim=(0,5),xlabel=r'$t/t_{\rm cc}$')
    ax.legend(frameon=False,fontsize=8);ax.grid(alpha=.15)
axs[0].set_ylabel(r'$M_{\rm d}/M_{\rm d}(0)$')
fig.savefig(ROOT/'figures/contrast_histories_updated.pdf',bbox_inches='tight')
plt.close(fig)
