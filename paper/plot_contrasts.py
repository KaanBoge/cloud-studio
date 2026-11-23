"""Plot the n = 128 grid histories at contrasts of 10 and 1000 (Figure 5).

Reads contrast_series.json (saved reductions) and writes figures/contrast_histories.pdf.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 11,
                     'pdf.fonttype': 42, 'ps.fonttype': 42})
NAMES = {'Enzo E': 'Enzo-E'}
STYLE = {'Enzo': ('#d17c1f', '-'), 'Enzo-E': ('#117a88', '-'), 'Athena++': ('#4b854b', '-'),
         'AthenaPK HLLE/PLM*': ('#684c9c', '--'), 'AthenaPK HLLC/PPM*': ('#a3487c', ':')}
ORDER = ['Enzo', 'Enzo-E', 'Athena++', 'AthenaPK HLLE/PLM*', 'AthenaPK HLLC/PPM*']


def main():
    rows = json.loads((ROOT / 'contrast_series.json').read_text())
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True, layout='constrained')
    for ax, chi in zip(axs, (10, 1000)):
        for name in ORDER:
            for row in rows:
                label = NAMES.get(row['label'], row['label'])
                if row['chi'] == chi and label == name:
                    color, ls = STYLE[name]
                    ax.plot(row['times'], row['dense'], color=color, ls=ls, lw=1.7, label=name)
        ax.text(0.96, 0.93, rf'$\chi={chi}$', transform=ax.transAxes, ha='right', va='top')
        ax.set(xlim=(0, 5), ylim=(0, 1.2), xlabel=r'$t/t_{\rm cc}$')
        ax.grid(alpha=.18)
    axs[0].set_ylabel(r'$M_{\rm d}/M_{\rm d}(0)$')
    axs[0].legend(loc='lower left', frameon=False, fontsize=9)
    fig.savefig(ROOT / 'figures' / 'contrast_histories.pdf', bbox_inches='tight')
    fig.savefig(ROOT / 'qa' / 'contrast_preview.png', dpi=110, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
