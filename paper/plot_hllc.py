"""Plot the AthenaPK HLLC/PPM histories (Figure 9) from saved reductions.

Reads validated_scalar_series_20261029.json and contrast_series.json and writes
figures/hllc_histories.pdf.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P = Path(__file__).resolve().parent
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 11,
                     'pdf.fonttype': 42, 'ps.fonttype': 42})


def main():
    rows = json.loads((P / 'validated_scalar_series_20261029.json').read_text())
    contrast = json.loads((P / 'contrast_series.json').read_text())
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True, layout='constrained')
    names = {'Cooling off': 'Non-radiative', 'Cooling on': 'Radiative'}
    for row, color in zip(rows[:2], ['#b65c1c', '#007c91']):
        axs[0].plot(row['times'], row['dense'], color=color, label=names.get(row['label'], row['label']), lw=1.8)
    axs[1].plot(rows[2]['times'], rows[2]['dense'], label='HLLC/PPM', color='#6652a0', lw=1.8)
    old = next(x for x in contrast if x['chi'] == 10 and 'HLLE' in x['label'])
    axs[1].plot(old['times'], old['dense'], label='HLLE/PLM', color='#777777', ls='--', lw=1.6)
    notes = [r'$\chi=100$, HLLC/PPM', r'$\chi=10$, non-radiative']
    for ax, note in zip(axs, notes):
        ax.text(0.96, 0.93, note, transform=ax.transAxes, ha='right', va='top')
        ax.set(xlim=(0, 5), ylim=(0, 1.2), xlabel=r'$t/t_{\rm cc}$')
        ax.grid(alpha=.18)
        ax.legend(loc='lower left', frameon=False, fontsize=9)
    axs[0].set_ylabel(r'$M_{\rm d}/M_{\rm d}(0)$')
    fig.savefig(P / 'figures' / 'hllc_histories.pdf', bbox_inches='tight')
    fig.savefig(P / 'qa' / 'hllc_preview.png', dpi=110, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
