"""Portable plot of saved reductions. No raw simulation files required."""
from pathlib import Path
import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
rows=json.loads((P/'validated_scalar_series_20261029.json').read_text())
contrast=json.loads((P/'contrast_series.json').read_text())
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(9,3.2),layout='constrained')
for row,color in zip(rows[:2],['#b65c1c','#007c91']):axs[0].plot(row['times'],row['dense'],color=color,label=row['label'],lw=1.8)
axs[0].set_title(r'$\chi=100$: HLLC/PPM variants')
axs[1].plot(rows[2]['times'],rows[2]['dense'],label='HLLC/PPM',color='#6652a0',lw=1.8)
old=next(x for x in contrast if x['chi']==10 and 'HLLE' in x['label'])
axs[1].plot(old['times'],old['dense'],label='Earlier HLLE/PLM',color='#777777',ls='--',lw=1.6)
axs[1].set_title(r'$\chi=10$: non-radiative variants')
for ax in axs:ax.set(xlim=(0,5),xlabel=r'$t/t_{\rm cc}$',ylabel=r'$M_{\rm d}/M_{\rm d}(0)$');ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
fig.savefig(P/'figures/hllc_validated_histories_20261029.pdf');plt.close(fig)
